"""Line-flow and power-balance utilities for Milestone 4."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.models import PowerSystemCase
from src.ybus import build_ybus
from src.ybus.admittance_utils import series_admittance, tap_complex


@dataclass(frozen=True)
class LineFlowRecord:
    from_bus: int
    to_bus: int
    p_from_mw: float
    q_from_mvar: float
    p_to_mw: float
    q_to_mvar: float
    p_loss_mw: float
    q_loss_mvar: float


def compute_line_flows(case: PowerSystemCase, voltages: np.ndarray) -> list[LineFlowRecord]:
    """Compute per-branch complex flows and losses from solved voltages."""
    if len(voltages) != len(case.buses):
        raise ValueError("voltages length must match number of buses")

    bus_idx = {bus.bus_i: idx for idx, bus in enumerate(case.buses)}
    base = case.base_mva
    results: list[LineFlowRecord] = []

    for branch in case.branches:
        if branch.status == 0:
            continue

        if branch.fbus not in bus_idx or branch.tbus not in bus_idx:
            raise ValueError(f"Branch references unknown bus {branch.fbus} -> {branch.tbus}")

        i = bus_idx[branch.fbus]
        j = bus_idx[branch.tbus]

        vi = voltages[i]
        vj = voltages[j]

        y = series_admittance(branch.r, branch.x)
        y_shunt = 1j * (branch.b / 2.0)
        tap = tap_complex(branch.ratio, branch.angle)
        tap_abs2 = abs(tap) ** 2

        # Consistent with Y-bus stamping used in build_ybus.
        i_from = ((y + y_shunt) / tap_abs2) * vi - (y / np.conj(tap)) * vj
        i_to = (-y / tap) * vi + (y + y_shunt) * vj

        s_from = vi * np.conj(i_from) * base
        s_to = vj * np.conj(i_to) * base
        s_loss = s_from + s_to

        results.append(
            LineFlowRecord(
                from_bus=branch.fbus,
                to_bus=branch.tbus,
                p_from_mw=float(s_from.real),
                q_from_mvar=float(s_from.imag),
                p_to_mw=float(s_to.real),
                q_to_mvar=float(s_to.imag),
                p_loss_mw=float(s_loss.real),
                q_loss_mvar=float(s_loss.imag),
            )
        )

    return results


def compute_power_balance(
    case: PowerSystemCase,
    voltages: np.ndarray,
    flows: list[LineFlowRecord],
) -> dict[str, float]:
    """Compute system-level active/reactive balance terms in MW/MVAr."""
    if len(voltages) != len(case.buses):
        raise ValueError("voltages length must match number of buses")

    ybus = build_ybus(case)
    s_inj = voltages * np.conj(ybus @ voltages) * case.base_mva
    p_net_inj = float(np.sum(s_inj.real))
    q_net_inj = float(np.sum(s_inj.imag))

    p_load = float(sum(bus.pd for bus in case.buses))
    q_load = float(sum(bus.qd for bus in case.buses))

    p_gen_est = p_load + p_net_inj
    q_gen_est = q_load + q_net_inj

    p_gen_sched = float(sum(gen.pg for gen in case.generators if gen.status == 1))
    q_gen_sched = float(sum(gen.qg for gen in case.generators if gen.status == 1))

    p_branch_loss = float(sum(flow.p_loss_mw for flow in flows))
    q_branch_loss = float(sum(flow.q_loss_mvar for flow in flows))

    vm2 = np.abs(voltages) ** 2
    p_bus_shunt_inj = float(sum(bus.gs * vm2[idx] for idx, bus in enumerate(case.buses)))
    q_bus_shunt_inj = float(sum(-bus.bs * vm2[idx] for idx, bus in enumerate(case.buses)))

    return {
        "p_generation_est_mw": p_gen_est,
        "q_generation_est_mvar": q_gen_est,
        "p_generation_sched_mw": p_gen_sched,
        "q_generation_sched_mvar": q_gen_sched,
        "p_load_mw": p_load,
        "q_load_mvar": q_load,
        "p_net_injection_mw": p_net_inj,
        "q_net_injection_mvar": q_net_inj,
        "p_branch_loss_mw": p_branch_loss,
        "q_branch_loss_mvar": q_branch_loss,
        "p_bus_shunt_injection_mw": p_bus_shunt_inj,
        "q_bus_shunt_injection_mvar": q_bus_shunt_inj,
        "p_balance_mw": p_gen_est - p_load - p_branch_loss - p_bus_shunt_inj,
        "q_balance_mvar": q_gen_est - q_load - q_branch_loss - q_bus_shunt_inj,
    }
