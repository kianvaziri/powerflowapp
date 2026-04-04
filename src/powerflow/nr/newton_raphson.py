"""Newton-Raphson power-flow solver for Milestone 3 (polar form)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.models import PowerSystemCase
from src.ybus import build_ybus

BUS_TYPE_PQ = 1
BUS_TYPE_PV = 2
BUS_TYPE_SLACK = 3


@dataclass(frozen=True)
class NRIterationRecord:
    iteration: int
    max_power_mismatch: float
    max_state_update: float
    jacobian_size: int


@dataclass(frozen=True)
class NRResult:
    voltages: np.ndarray
    converged: bool
    iterations: int
    history: list[NRIterationRecord]


def solve_newton_raphson(
    case: PowerSystemCase,
    tolerance: float = 1e-6,
    max_iterations: int = 50,
) -> NRResult:
    """Solve power flow using Newton-Raphson in polar coordinates."""
    if tolerance <= 0:
        raise ValueError("tolerance must be positive")
    if max_iterations <= 0:
        raise ValueError("max_iterations must be positive")

    ybus = build_ybus(case)
    g = ybus.real
    b = ybus.imag

    bus_types = np.array([bus.bus_type for bus in case.buses], dtype=int)

    slack = np.where(bus_types == BUS_TYPE_SLACK)[0]
    if len(slack) != 1:
        raise ValueError(f"Expected exactly one slack bus, found {len(slack)}")

    pv = np.where(bus_types == BUS_TYPE_PV)[0]
    pq = np.where(bus_types == BUS_TYPE_PQ)[0]

    p_rows = np.concatenate([pv, pq])
    q_rows = pq.copy()

    p_spec, q_spec = _build_specified_power_injections(case)

    vm = np.array([bus.vm for bus in case.buses], dtype=float)
    va = np.radians(np.array([bus.va for bus in case.buses], dtype=float))

    pv_vm_targets = vm[pv].copy()
    slack_vm_target = vm[slack[0]]
    slack_va_target = va[slack[0]]

    history: list[NRIterationRecord] = []

    for it in range(1, max_iterations + 1):
        p_calc, q_calc = _calc_power_injections(vm, va, g, b)

        dp = p_spec[p_rows] - p_calc[p_rows]
        dq = q_spec[q_rows] - q_calc[q_rows]
        mismatch = np.concatenate([dp, dq])

        max_mismatch_before = float(np.max(np.abs(mismatch))) if mismatch.size > 0 else 0.0
        if max_mismatch_before < tolerance:
            return NRResult(
                voltages=vm * np.exp(1j * va),
                converged=True,
                iterations=it - 1,
                history=history,
            )

        jacobian = _build_jacobian(
            vm=vm,
            va=va,
            g=g,
            b=b,
            p_calc=p_calc,
            q_calc=q_calc,
            p_rows=p_rows,
            q_rows=q_rows,
        )

        dx = np.linalg.solve(jacobian, mismatch)

        n_p = len(p_rows)
        dtheta = dx[:n_p]
        dvm = dx[n_p:]

        va[p_rows] += dtheta
        vm[q_rows] += dvm

        # Enforce fixed magnitudes for slack and PV buses.
        vm[slack[0]] = slack_vm_target
        va[slack[0]] = slack_va_target
        vm[pv] = pv_vm_targets

        # Evaluate mismatch after update so history reflects true post-step convergence.
        p_after, q_after = _calc_power_injections(vm, va, g, b)
        dp_after = p_spec[p_rows] - p_after[p_rows]
        dq_after = q_spec[q_rows] - q_after[q_rows]
        mismatch_after = np.concatenate([dp_after, dq_after])
        max_mismatch_after = (
            float(np.max(np.abs(mismatch_after))) if mismatch_after.size > 0 else 0.0
        )

        max_update = float(np.max(np.abs(dx))) if dx.size > 0 else 0.0
        history.append(
            NRIterationRecord(
                iteration=it,
                max_power_mismatch=max_mismatch_after,
                max_state_update=max_update,
                jacobian_size=int(jacobian.shape[0]),
            )
        )

        if max_mismatch_after < tolerance:
            return NRResult(
                voltages=vm * np.exp(1j * va),
                converged=True,
                iterations=it,
                history=history,
            )

    return NRResult(
        voltages=vm * np.exp(1j * va),
        converged=False,
        iterations=max_iterations,
        history=history,
    )


def _build_specified_power_injections(case: PowerSystemCase) -> tuple[np.ndarray, np.ndarray]:
    """Return net specified P and Q injections in per-unit (generation - load)."""
    bus_to_idx = {bus.bus_i: idx for idx, bus in enumerate(case.buses)}
    nbus = len(case.buses)

    p = np.zeros(nbus, dtype=float)
    q = np.zeros(nbus, dtype=float)

    for bus in case.buses:
        idx = bus_to_idx[bus.bus_i]
        p[idx] -= bus.pd / case.base_mva
        q[idx] -= bus.qd / case.base_mva

    for gen in case.generators:
        if gen.status == 0:
            continue
        if gen.bus not in bus_to_idx:
            raise ValueError(f"Generator references unknown bus {gen.bus}")
        idx = bus_to_idx[gen.bus]
        p[idx] += gen.pg / case.base_mva
        q[idx] += gen.qg / case.base_mva

    return p, q


def _calc_power_injections(
    vm: np.ndarray,
    va: np.ndarray,
    g: np.ndarray,
    b: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    nbus = len(vm)
    p = np.zeros(nbus, dtype=float)
    q = np.zeros(nbus, dtype=float)

    for i in range(nbus):
        for k in range(nbus):
            dth = va[i] - va[k]
            p[i] += vm[i] * vm[k] * (g[i, k] * np.cos(dth) + b[i, k] * np.sin(dth))
            q[i] += vm[i] * vm[k] * (g[i, k] * np.sin(dth) - b[i, k] * np.cos(dth))

    return p, q


def _build_jacobian(
    vm: np.ndarray,
    va: np.ndarray,
    g: np.ndarray,
    b: np.ndarray,
    p_calc: np.ndarray,
    q_calc: np.ndarray,
    p_rows: np.ndarray,
    q_rows: np.ndarray,
) -> np.ndarray:
    """Build full NR Jacobian blocks [H N; M L] for current iterate."""
    n_p = len(p_rows)
    n_q = len(q_rows)
    j = np.zeros((n_p + n_q, n_p + n_q), dtype=float)

    # H and N blocks (dP/dTheta, dP/dV)
    for r, i in enumerate(p_rows):
        for c, k in enumerate(p_rows):
            if i == k:
                j[r, c] = -q_calc[i] - b[i, i] * vm[i] ** 2
            else:
                dth = va[i] - va[k]
                j[r, c] = vm[i] * vm[k] * (g[i, k] * np.sin(dth) - b[i, k] * np.cos(dth))

        for c, k in enumerate(q_rows):
            col = n_p + c
            if i == k:
                j[r, col] = p_calc[i] / vm[i] + g[i, i] * vm[i]
            else:
                dth = va[i] - va[k]
                j[r, col] = vm[i] * (g[i, k] * np.cos(dth) + b[i, k] * np.sin(dth))

    # M and L blocks (dQ/dTheta, dQ/dV)
    for r, i in enumerate(q_rows):
        row = n_p + r

        for c, k in enumerate(p_rows):
            if i == k:
                j[row, c] = p_calc[i] - g[i, i] * vm[i] ** 2
            else:
                dth = va[i] - va[k]
                j[row, c] = -vm[i] * vm[k] * (g[i, k] * np.cos(dth) + b[i, k] * np.sin(dth))

        for c, k in enumerate(q_rows):
            col = n_p + c
            if i == k:
                j[row, col] = q_calc[i] / vm[i] - b[i, i] * vm[i]
            else:
                dth = va[i] - va[k]
                j[row, col] = vm[i] * (g[i, k] * np.sin(dth) - b[i, k] * np.cos(dth))

    return j
