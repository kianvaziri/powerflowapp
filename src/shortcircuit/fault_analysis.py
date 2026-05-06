"""Short-circuit fault analysis utilities for Milestone 5."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.models import PowerSystemCase
from src.ybus.admittance_utils import series_admittance, tap_complex

FAULT_TYPE_3PH = "3PH"
FAULT_TYPE_LG = "LG"
FAULT_TYPE_LL = "LL"
FAULT_TYPE_LLG = "LLG"

SUPPORTED_FAULT_TYPES = {
    FAULT_TYPE_3PH,
    FAULT_TYPE_LG,
    FAULT_TYPE_LL,
    FAULT_TYPE_LLG,
}

# Common utility default when branch zero-sequence data is unavailable.
DEFAULT_BRANCH_ZERO_SEQ_SCALE = 2.5

A = np.exp(1j * 2.0 * np.pi / 3.0)


@dataclass(frozen=True)
class FaultAnalysisResult:
    fault_type: str
    fault_bus: int
    fault_bus_index: int
    fault_impedance_pu: complex
    z0_th_pu: complex
    z1_th_pu: complex
    z2_th_pu: complex
    i0_pu: complex
    i1_pu: complex
    i2_pu: complex
    ia_pu: complex
    ib_pu: complex
    ic_pu: complex
    post_v0_pu: np.ndarray
    post_v1_pu: np.ndarray
    post_v2_pu: np.ndarray
    post_va_pu: np.ndarray
    post_vb_pu: np.ndarray
    post_vc_pu: np.ndarray


def build_sequence_ybus(
    case: PowerSystemCase,
    default_gen_xdpp_pu: float = 0.2,
    gen_x1_pu_by_bus: dict[int, float] | None = None,
    gen_x2_pu_by_bus: dict[int, float] | None = None,
    gen_x0_pu_by_bus: dict[int, float] | None = None,
    branch_zero_seq_scale: float = DEFAULT_BRANCH_ZERO_SEQ_SCALE,
    branch_zero_seq_scale_by_branch: dict[tuple[int, int], float] | None = None,
    zero_seq_blocked_branches: set[tuple[int, int]] | None = None,
    include_bus_shunts: bool = False,
    include_line_charging: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build positive, negative, and zero-sequence Y-bus approximations.

    Assumptions used in this implementation:
    - Positive sequence follows load-flow branch R/X data.
    - Negative sequence uses the same branch R/X values, with opposite phase-shift
      sign on tap angles.
    - Zero sequence defaults to a scaled positive-sequence branch impedance model
      when explicit sequence branch data is unavailable.
    - Generator sequence reactances are modeled as shunts to ground at generator
      buses for fault-network Thevenin construction.
    """
    if default_gen_xdpp_pu <= 0:
        raise ValueError("default_gen_xdpp_pu must be positive")
    if branch_zero_seq_scale <= 0:
        raise ValueError("branch_zero_seq_scale must be positive")

    branch_scale_map = branch_zero_seq_scale_by_branch or {}
    blocked_zero_seq = zero_seq_blocked_branches or set()

    nbus = len(case.buses)
    bus_to_idx = {bus.bus_i: idx for idx, bus in enumerate(case.buses)}

    y1 = np.zeros((nbus, nbus), dtype=complex)
    y2 = np.zeros((nbus, nbus), dtype=complex)
    y0 = np.zeros((nbus, nbus), dtype=complex)

    if include_bus_shunts:
        for bus in case.buses:
            idx = bus_to_idx[bus.bus_i]
            y_shunt = complex(bus.gs, bus.bs) / case.base_mva
            y1[idx, idx] += y_shunt
            y2[idx, idx] += y_shunt
            y0[idx, idx] += y_shunt

    for branch in case.branches:
        if branch.status == 0:
            continue

        if branch.fbus not in bus_to_idx or branch.tbus not in bus_to_idx:
            raise ValueError(f"Branch references unknown bus: {branch.fbus} -> {branch.tbus}")

        i = bus_to_idx[branch.fbus]
        j = bus_to_idx[branch.tbus]

        shunt_b = branch.b if include_line_charging else 0.0

        # Positive sequence.
        _stamp_branch(
            ybus=y1,
            i=i,
            j=j,
            r=branch.r,
            x=branch.x,
            shunt_b=shunt_b,
            tap_ratio=branch.ratio,
            tap_angle_deg=branch.angle,
        )

        # Negative sequence (phase shift sign reverses).
        _stamp_branch(
            ybus=y2,
            i=i,
            j=j,
            r=branch.r,
            x=branch.x,
            shunt_b=shunt_b,
            tap_ratio=branch.ratio,
            tap_angle_deg=-branch.angle,
        )

        # Zero sequence (scaled branch impedance approximation).
        branch_key = _branch_key(branch.fbus, branch.tbus)
        if branch_key in blocked_zero_seq:
            continue

        z_pos = complex(branch.r, branch.x)
        if abs(z_pos) < 1e-14:
            raise ValueError("Branch impedance r + jx is zero; cannot compute sequence admittance")

        local_scale = branch_scale_map.get(branch_key, branch_zero_seq_scale)
        if local_scale <= 0:
            raise ValueError(f"Branch zero-sequence scale must be positive for branch {branch.fbus}-{branch.tbus}")
        z_zero = local_scale * z_pos

        _stamp_branch(
            ybus=y0,
            i=i,
            j=j,
            r=float(z_zero.real),
            x=float(z_zero.imag),
            shunt_b=shunt_b,
            tap_ratio=branch.ratio,
            tap_angle_deg=0.0,
        )

    x1_map = gen_x1_pu_by_bus or {}
    x2_map = gen_x2_pu_by_bus or {}
    x0_map = gen_x0_pu_by_bus or {}

    for gen in case.generators:
        if gen.status == 0:
            continue
        if gen.bus not in bus_to_idx:
            raise ValueError(f"Generator references unknown bus {gen.bus}")

        idx = bus_to_idx[gen.bus]
        x1 = x1_map.get(gen.bus, default_gen_xdpp_pu)
        x2 = x2_map.get(gen.bus, x1)
        x0 = x0_map.get(gen.bus, x1)

        if x1 <= 0 or x2 <= 0 or x0 <= 0:
            raise ValueError("Generator sequence reactances must be positive")

        y1[idx, idx] += 1.0 / (1j * x1)
        y2[idx, idx] += 1.0 / (1j * x2)
        y0[idx, idx] += 1.0 / (1j * x0)

    return y1, y2, y0


def analyze_fault(
    case: PowerSystemCase,
    pre_fault_voltages: np.ndarray,
    fault_bus: int,
    fault_type: str,
    fault_impedance_pu: complex | float = 0.0,
    default_gen_xdpp_pu: float = 0.2,
    gen_x1_pu_by_bus: dict[int, float] | None = None,
    gen_x2_pu_by_bus: dict[int, float] | None = None,
    gen_x0_pu_by_bus: dict[int, float] | None = None,
    branch_zero_seq_scale: float = DEFAULT_BRANCH_ZERO_SEQ_SCALE,
    branch_zero_seq_scale_by_branch: dict[tuple[int, int], float] | None = None,
    zero_seq_blocked_branches: set[tuple[int, int]] | None = None,
    include_bus_shunts: bool = False,
    include_line_charging: bool = False,
) -> FaultAnalysisResult:
    """Analyze a short-circuit fault using sequence-network methods."""
    if len(pre_fault_voltages) != len(case.buses):
        raise ValueError("pre_fault_voltages length must match number of buses")

    fault_code = fault_type.strip().upper()
    if fault_code not in SUPPORTED_FAULT_TYPES:
        raise ValueError(f"Unsupported fault_type '{fault_type}'")

    bus_to_idx = {bus.bus_i: idx for idx, bus in enumerate(case.buses)}
    if fault_bus not in bus_to_idx:
        raise ValueError(f"Unknown fault_bus {fault_bus}")

    k = bus_to_idx[fault_bus]
    zf = complex(fault_impedance_pu)

    y1, y2, y0 = build_sequence_ybus(
        case,
        default_gen_xdpp_pu=default_gen_xdpp_pu,
        gen_x1_pu_by_bus=gen_x1_pu_by_bus,
        gen_x2_pu_by_bus=gen_x2_pu_by_bus,
        gen_x0_pu_by_bus=gen_x0_pu_by_bus,
        branch_zero_seq_scale=branch_zero_seq_scale,
        branch_zero_seq_scale_by_branch=branch_zero_seq_scale_by_branch,
        zero_seq_blocked_branches=zero_seq_blocked_branches,
        include_bus_shunts=include_bus_shunts,
        include_line_charging=include_line_charging,
    )

    z1 = _inverse_stable(y1)
    z2 = _inverse_stable(y2)
    z0 = _inverse_stable(y0)

    v_prefault = pre_fault_voltages.astype(complex)
    v1_th = v_prefault[k]
    z1_th = z1[k, k]
    z2_th = z2[k, k]
    z0_th = z0[k, k]

    i0, i1, i2 = _solve_sequence_currents(
        fault_code=fault_code,
        v1_th=v1_th,
        z1_th=z1_th,
        z2_th=z2_th,
        z0_th=z0_th,
        zf=zf,
    )

    v1_post = v_prefault - z1[:, k] * i1
    v2_post = -z2[:, k] * i2
    v0_post = -z0[:, k] * i0

    va_post, vb_post, vc_post = _sequence_to_phase(v0_post, v1_post, v2_post)
    ia, ib, ic = _sequence_to_phase(i0, i1, i2)

    return FaultAnalysisResult(
        fault_type=fault_code,
        fault_bus=fault_bus,
        fault_bus_index=k,
        fault_impedance_pu=zf,
        z0_th_pu=z0_th,
        z1_th_pu=z1_th,
        z2_th_pu=z2_th,
        i0_pu=i0,
        i1_pu=i1,
        i2_pu=i2,
        ia_pu=ia,
        ib_pu=ib,
        ic_pu=ic,
        post_v0_pu=v0_post,
        post_v1_pu=v1_post,
        post_v2_pu=v2_post,
        post_va_pu=va_post,
        post_vb_pu=vb_post,
        post_vc_pu=vc_post,
    )


def fault_current_rows(result: FaultAnalysisResult) -> list[dict[str, float | str | int]]:
    """Return tabular rows for sequence and phase fault currents."""
    rows: list[dict[str, float | str | int]] = []

    def _row(name: str, value: complex) -> dict[str, float | str | int]:
        return {
            "quantity": name,
            "real_pu": float(value.real),
            "imag_pu": float(value.imag),
            "mag_pu": float(abs(value)),
            "ang_deg": float(np.degrees(np.angle(value))),
        }

    rows.append(_row("I0", result.i0_pu))
    rows.append(_row("I1", result.i1_pu))
    rows.append(_row("I2", result.i2_pu))
    rows.append(_row("Ia", result.ia_pu))
    rows.append(_row("Ib", result.ib_pu))
    rows.append(_row("Ic", result.ic_pu))
    return rows


def post_fault_voltage_rows(
    case: PowerSystemCase,
    result: FaultAnalysisResult,
) -> list[dict[str, float | int]]:
    """Return tabular rows for per-bus post-fault phase voltages."""
    rows: list[dict[str, float | int]] = []
    for idx, bus in enumerate(case.buses):
        va = result.post_va_pu[idx]
        vb = result.post_vb_pu[idx]
        vc = result.post_vc_pu[idx]
        rows.append(
            {
                "bus": bus.bus_i,
                "va_mag_pu": float(abs(va)),
                "va_ang_deg": float(np.degrees(np.angle(va))),
                "vb_mag_pu": float(abs(vb)),
                "vb_ang_deg": float(np.degrees(np.angle(vb))),
                "vc_mag_pu": float(abs(vc)),
                "vc_ang_deg": float(np.degrees(np.angle(vc))),
            }
        )
    return rows


def _solve_sequence_currents(
    fault_code: str,
    v1_th: complex,
    z1_th: complex,
    z2_th: complex,
    z0_th: complex,
    zf: complex,
) -> tuple[complex, complex, complex]:
    if fault_code == FAULT_TYPE_3PH:
        den = z1_th + zf
        i1 = _safe_div(v1_th, den, "3PH fault denominator is zero")
        return 0.0 + 0.0j, i1, 0.0 + 0.0j

    if fault_code == FAULT_TYPE_LG:
        den = z1_th + z2_th + z0_th + 3.0 * zf
        i1 = _safe_div(v1_th, den, "LG fault denominator is zero")
        return i1, i1, i1

    if fault_code == FAULT_TYPE_LL:
        den = z1_th + z2_th + zf
        i1 = _safe_div(v1_th, den, "LL fault denominator is zero")
        i2 = -i1
        return 0.0 + 0.0j, i1, i2

    # LLG fault
    den_parallel = z2_th + z0_th + 3.0 * zf
    if abs(den_parallel) < 1e-14:
        raise ValueError("LLG fault denominator is zero")

    z_eq = (z2_th * (z0_th + 3.0 * zf)) / den_parallel
    i1 = _safe_div(v1_th, z1_th + z_eq, "LLG fault denominator is zero")
    i2 = -i1 * (z0_th + 3.0 * zf) / den_parallel
    i0 = -i1 * z2_th / den_parallel
    return i0, i1, i2



def _branch_key(fbus: int, tbus: int) -> tuple[int, int]:
    if fbus <= tbus:
        return fbus, tbus
    return tbus, fbus


def _stamp_branch(
    ybus: np.ndarray,
    i: int,
    j: int,
    r: float,
    x: float,
    shunt_b: float,
    tap_ratio: float,
    tap_angle_deg: float,
) -> None:
    y_series = series_admittance(r, x)
    y_shunt = 1j * (shunt_b / 2.0)
    tap = tap_complex(tap_ratio, tap_angle_deg)

    ybus[i, i] += (y_series + y_shunt) / (tap * tap.conjugate())
    ybus[j, j] += y_series + y_shunt
    ybus[i, j] -= y_series / tap.conjugate()
    ybus[j, i] -= y_series / tap


def _safe_div(num: complex, den: complex, err_msg: str) -> complex:
    if abs(den) < 1e-14:
        raise ValueError(err_msg)
    return num / den


def _inverse_stable(y: np.ndarray) -> np.ndarray:
    try:
        return np.linalg.inv(y)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(y)


def _sequence_to_phase(
    v0: np.ndarray | complex,
    v1: np.ndarray | complex,
    v2: np.ndarray | complex,
) -> tuple[np.ndarray | complex, np.ndarray | complex, np.ndarray | complex]:
    va = v0 + v1 + v2
    vb = v0 + (A**2) * v1 + A * v2
    vc = v0 + A * v1 + (A**2) * v2
    return va, vb, vc
