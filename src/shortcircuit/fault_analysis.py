"""Short-circuit fault analysis utilities for Milestone 5."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.models import PowerSystemCase
from src.ybus import build_ybus

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

A = np.exp(1j * 2.0 * np.pi / 3.0)


@dataclass(frozen=True)
class FaultAnalysisResult:
    fault_type: str
    fault_bus: int
    fault_bus_index: int
    fault_impedance_pu: complex
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
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build positive, negative, and zero-sequence Y-bus approximations.

    Assumptions used for M5 implementation:
    - Branch negative/zero-sequence parameters are approximated by the same values as
      positive sequence when dedicated sequence data is unavailable.
    - Generator subtransient reactance defaults to `default_gen_xdpp_pu` if not provided
      explicitly by bus in mapping dictionaries.
    """
    if default_gen_xdpp_pu <= 0:
        raise ValueError("default_gen_xdpp_pu must be positive")

    y_base = build_ybus(case)
    y1 = y_base.astype(complex).copy()
    y2 = y_base.astype(complex).copy()
    y0 = y_base.astype(complex).copy()

    bus_to_idx = {bus.bus_i: idx for idx, bus in enumerate(case.buses)}
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
