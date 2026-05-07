"""Short-circuit fault analysis utilities for Milestone 5."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.models import Generator, PowerSystemCase
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
_EPS = 1e-14


@dataclass(frozen=True)
class FaultAnalysisResult:
    fault_type: str
    fault_bus: int
    fault_bus_index: int
    fault_impedance_pu: complex
    z0_th_pu: complex
    z1_th_pu: complex
    z2_th_pu: complex
    fault_denominator_pu: complex
    llg_parallel_denominator_pu: complex | None
    z0_inversion_method: str
    z1_inversion_method: str
    z2_inversion_method: str
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
    sequence_data_on_gen_mbase: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build positive, negative, and zero-sequence Y-bus matrices.

    Explicit sequence fields from the parsed case are used when available. If a
    case file does not contain sequence data, the previous approximations remain
    in effect: negative sequence follows positive sequence, and zero sequence is
    estimated by scaling positive-sequence branch impedance.
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

    for bus in case.buses:
        idx = bus_to_idx[bus.bus_i]
        y1[idx, idx] += complex(bus.seq_g1, bus.seq_b1)
        y2[idx, idx] += complex(bus.seq_g2, bus.seq_b2)
        y0[idx, idx] += complex(bus.seq_g0, bus.seq_b0)
        if include_bus_shunts:
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

        shunt_b1 = branch.b if include_line_charging else 0.0
        _stamp_branch(
            ybus=y1,
            i=i,
            j=j,
            r=branch.r,
            x=branch.x,
            shunt_b=shunt_b1,
            tap_ratio=branch.ratio,
            tap_angle_deg=branch.angle,
        )

        r2 = branch.r if branch.r2 is None else branch.r2
        x2 = branch.x if branch.x2 is None else branch.x2
        b2 = branch.b if branch.b2 is None else branch.b2
        shunt_b2 = b2 if include_line_charging else 0.0
        _stamp_branch(
            ybus=y2,
            i=i,
            j=j,
            r=r2,
            x=x2,
            shunt_b=shunt_b2,
            tap_ratio=branch.ratio,
            tap_angle_deg=-branch.angle,
        )

        branch_key = _branch_key(branch.fbus, branch.tbus)
        if branch_key in blocked_zero_seq or branch.zero_sequence_status == 0:
            continue

        if branch.r0 is not None and branch.x0 is not None:
            r0 = branch.r0
            x0 = branch.x0
            b0 = branch.b0 if branch.b0 is not None else 0.0
        else:
            z_pos = complex(branch.r, branch.x)
            if abs(z_pos) < _EPS:
                raise ValueError("Branch impedance r + jx is zero; cannot compute sequence admittance")
            local_scale = branch_scale_map.get(branch_key, branch_zero_seq_scale)
            if local_scale <= 0:
                raise ValueError(
                    f"Branch zero-sequence scale must be positive for branch {branch.fbus}-{branch.tbus}"
                )
            z_zero = local_scale * z_pos
            r0 = float(z_zero.real)
            x0 = float(z_zero.imag)
            b0 = branch.b if include_line_charging else 0.0

        _stamp_branch(
            ybus=y0,
            i=i,
            j=j,
            r=r0,
            x=x0,
            shunt_b=b0 if include_line_charging else 0.0,
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
        z1, z2, z0 = _generator_sequence_impedances(
            gen=gen,
            case_base_mva=case.base_mva,
            default_gen_xdpp_pu=default_gen_xdpp_pu,
            gen_x1_pu_by_bus=x1_map,
            gen_x2_pu_by_bus=x2_map,
            gen_x0_pu_by_bus=x0_map,
            sequence_data_on_gen_mbase=sequence_data_on_gen_mbase,
        )

        y1[idx, idx] += _safe_admittance(z1, f"Generator {gen.bus} positive-sequence impedance is zero")
        y2[idx, idx] += _safe_admittance(z2, f"Generator {gen.bus} negative-sequence impedance is zero")
        y0[idx, idx] += _safe_admittance(z0, f"Generator {gen.bus} zero-sequence impedance path is zero")

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
    sequence_data_on_gen_mbase: bool = True,
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
        sequence_data_on_gen_mbase=sequence_data_on_gen_mbase,
    )

    z1, z1_method = _inverse_with_method(y1)
    z2, z2_method = _inverse_with_method(y2)
    z0, z0_method = _inverse_with_method(y0)

    v_prefault = pre_fault_voltages.astype(complex)
    v1_th = v_prefault[k]
    z1_th = z1[k, k]
    z2_th = z2[k, k]
    z0_th = z0[k, k]

    i0, i1, i2, fault_denominator, llg_parallel_denominator = _solve_sequence_currents(
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
        fault_denominator_pu=fault_denominator,
        llg_parallel_denominator_pu=llg_parallel_denominator,
        z0_inversion_method=z0_method,
        z1_inversion_method=z1_method,
        z2_inversion_method=z2_method,
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


def fault_diagnostic_rows(result: FaultAnalysisResult) -> list[dict[str, float | str | int]]:
    """Return Thevenin and denominator diagnostics for PowerWorld comparisons."""
    rows: list[dict[str, float | str | int]] = []

    def _complex_row(name: str, value: complex, method: str = "", note: str = "") -> dict[str, float | str | int]:
        return {
            "quantity": name,
            "real_pu": float(value.real),
            "imag_pu": float(value.imag),
            "mag_pu": float(abs(value)),
            "ang_deg": float(np.degrees(np.angle(value))),
            "method": method,
            "note": note,
        }

    rows.append(_complex_row("Z0_th", result.z0_th_pu, result.z0_inversion_method))
    rows.append(_complex_row("Z1_th", result.z1_th_pu, result.z1_inversion_method))
    rows.append(_complex_row("Z2_th", result.z2_th_pu, result.z2_inversion_method))
    rows.append(_complex_row("Fault impedance Zf", result.fault_impedance_pu))

    if result.fault_type == FAULT_TYPE_LG:
        denominator_name = "SLG denominator Z0+Z1+Z2+3Zf"
    elif result.fault_type == FAULT_TYPE_3PH:
        denominator_name = "3PH denominator Z1+Zf"
    elif result.fault_type == FAULT_TYPE_LL:
        denominator_name = "LL denominator Z1+Z2+Zf"
    else:
        denominator_name = "DLG denominator Z1+parallel(Z2, Z0+3Zf)"
    rows.append(_complex_row(denominator_name, result.fault_denominator_pu))

    if result.llg_parallel_denominator_pu is not None:
        rows.append(
            _complex_row(
                "DLG parallel denominator Z2+Z0+3Zf",
                result.llg_parallel_denominator_pu,
            )
        )

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
) -> tuple[complex, complex, complex, complex, complex | None]:
    if fault_code == FAULT_TYPE_3PH:
        den = z1_th + zf
        i1 = _safe_div(v1_th, den, "3PH fault denominator is zero")
        return 0.0 + 0.0j, i1, 0.0 + 0.0j, den, None

    if fault_code == FAULT_TYPE_LG:
        den = z1_th + z2_th + z0_th + 3.0 * zf
        i1 = _safe_div(v1_th, den, "LG fault denominator is zero")
        return i1, i1, i1, den, None

    if fault_code == FAULT_TYPE_LL:
        den = z1_th + z2_th + zf
        i1 = _safe_div(v1_th, den, "LL fault denominator is zero")
        i2 = -i1
        return 0.0 + 0.0j, i1, i2, den, None

    den_parallel = z2_th + z0_th + 3.0 * zf
    if abs(den_parallel) < _EPS:
        raise ValueError("LLG fault denominator is zero")

    z_eq = (z2_th * (z0_th + 3.0 * zf)) / den_parallel
    den = z1_th + z_eq
    i1 = _safe_div(v1_th, den, "LLG fault denominator is zero")
    i2 = -i1 * (z0_th + 3.0 * zf) / den_parallel
    i0 = -i1 * z2_th / den_parallel
    return i0, i1, i2, den, den_parallel


def _generator_sequence_impedances(
    gen: Generator,
    case_base_mva: float,
    default_gen_xdpp_pu: float,
    gen_x1_pu_by_bus: dict[int, float],
    gen_x2_pu_by_bus: dict[int, float],
    gen_x0_pu_by_bus: dict[int, float],
    sequence_data_on_gen_mbase: bool,
) -> tuple[complex, complex, complex]:
    z_default = complex(0.0, default_gen_xdpp_pu)
    z1_raw = _generator_sequence_impedance_raw(gen, 1, gen_x1_pu_by_bus, z_default)
    z2_raw = _generator_sequence_impedance_raw(gen, 2, gen_x2_pu_by_bus, z1_raw)
    z0_raw = _generator_sequence_impedance_raw(gen, 0, gen_x0_pu_by_bus, z1_raw)
    zn_raw = complex(gen.rn, gen.xn)

    z1 = _to_system_base(z1_raw, gen, case_base_mva, sequence_data_on_gen_mbase)
    z2 = _to_system_base(z2_raw, gen, case_base_mva, sequence_data_on_gen_mbase)
    z0 = _to_system_base(z0_raw + 3.0 * zn_raw, gen, case_base_mva, sequence_data_on_gen_mbase)
    return z1, z2, z0


def _generator_sequence_impedance_raw(
    gen: Generator,
    sequence: int,
    override_by_bus: dict[int, float],
    fallback: complex,
) -> complex:
    if gen.bus in override_by_bus:
        return complex(0.0, override_by_bus[gen.bus])

    r_attr = f"r{sequence}"
    x_attr = f"x{sequence}"
    r_value = getattr(gen, r_attr)
    x_value = getattr(gen, x_attr)
    if x_value is None:
        return fallback
    return complex(0.0 if r_value is None else float(r_value), float(x_value))


def _to_system_base(z_pu: complex, gen: Generator, case_base_mva: float, enabled: bool) -> complex:
    if not enabled:
        return z_pu
    if gen.mbase <= 0.0:
        raise ValueError(f"Generator at bus {gen.bus} has non-positive mBase")
    return z_pu * (case_base_mva / gen.mbase)


def _safe_admittance(z: complex, err_msg: str) -> complex:
    if abs(z) < _EPS:
        raise ValueError(err_msg)
    return 1.0 / z


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
    if abs(den) < _EPS:
        raise ValueError(err_msg)
    return num / den


def _inverse_with_method(y: np.ndarray) -> tuple[np.ndarray, str]:
    try:
        return np.linalg.inv(y), "inverse"
    except np.linalg.LinAlgError:
        return np.linalg.pinv(y), "pseudo-inverse"


def _sequence_to_phase(
    v0: np.ndarray | complex,
    v1: np.ndarray | complex,
    v2: np.ndarray | complex,
) -> tuple[np.ndarray | complex, np.ndarray | complex, np.ndarray | complex]:
    va = v0 + v1 + v2
    vb = v0 + (A**2) * v1 + A * v2
    vc = v0 + A * v1 + (A**2) * v2
    return va, vb, vc
