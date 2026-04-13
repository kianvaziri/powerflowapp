from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.parser import parse_matpower_case
from src.powerflow.nr import solve_newton_raphson
from src.shortcircuit import analyze_fault, build_sequence_ybus
from src.ybus import build_ybus


def _data_path(*parts: str) -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "raw" / Path(*parts)


def _prefault_solution(case_path: Path) -> tuple:
    case = parse_matpower_case(case_path)
    result = solve_newton_raphson(case, tolerance=1e-10, max_iterations=50)
    assert result.converged
    return case, result.voltages


def test_sequence_ybus_includes_generator_subtransient_reactance() -> None:
    case = parse_matpower_case(_data_path("small_cases", "case3_sample.m"))
    y_base = build_ybus(case)

    y1, y2, y0 = build_sequence_ybus(case, default_gen_xdpp_pu=0.2)

    # Bus 1 has an online generator in case3; adding 1/(j*0.2) = -j5 to diagonal.
    expected_delta = 1.0 / (1j * 0.2)
    assert y1[0, 0] - y_base[0, 0] == pytest.approx(expected_delta)
    assert y2[0, 0] - y_base[0, 0] == pytest.approx(expected_delta)
    assert y0[0, 0] - y_base[0, 0] == pytest.approx(expected_delta)


def test_three_phase_fault_has_only_positive_sequence_current() -> None:
    case, v_prefault = _prefault_solution(_data_path("small_cases", "case3_sample.m"))

    result = analyze_fault(
        case=case,
        pre_fault_voltages=v_prefault,
        fault_bus=2,
        fault_type="3PH",
        fault_impedance_pu=0.0,
    )

    assert result.i0_pu == pytest.approx(0.0 + 0.0j, abs=1e-12)
    assert result.i2_pu == pytest.approx(0.0 + 0.0j, abs=1e-12)
    assert abs(result.i1_pu) > 0.0

    fault_idx = result.fault_bus_index
    assert abs(result.post_va_pu[fault_idx]) < 1e-8


def test_lg_fault_sequence_relationships_hold() -> None:
    case, v_prefault = _prefault_solution(_data_path("small_cases", "case3_sample.m"))

    result = analyze_fault(
        case=case,
        pre_fault_voltages=v_prefault,
        fault_bus=2,
        fault_type="LG",
        fault_impedance_pu=0.0,
    )

    assert result.i0_pu == pytest.approx(result.i1_pu, abs=1e-10)
    assert result.i2_pu == pytest.approx(result.i1_pu, abs=1e-10)
    assert result.ia_pu == pytest.approx(3.0 * result.i1_pu, abs=1e-10)
    assert abs(result.ib_pu) < 1e-8
    assert abs(result.ic_pu) < 1e-8


def test_ll_fault_has_zero_zero_sequence_and_zero_phase_a_current() -> None:
    case, v_prefault = _prefault_solution(_data_path("small_cases", "case3_sample.m"))

    result = analyze_fault(
        case=case,
        pre_fault_voltages=v_prefault,
        fault_bus=3,
        fault_type="LL",
        fault_impedance_pu=0.0,
    )

    assert abs(result.i0_pu) < 1e-10
    assert abs(result.ia_pu) < 1e-8
    assert abs(result.ib_pu) > 0.0
    assert abs(result.ic_pu) > 0.0


def test_llg_fault_returns_finite_currents_and_voltages() -> None:
    case, v_prefault = _prefault_solution(_data_path("ieee14", "case14_sample.m"))

    result = analyze_fault(
        case=case,
        pre_fault_voltages=v_prefault,
        fault_bus=4,
        fault_type="LLG",
        fault_impedance_pu=0.0,
    )

    assert np.isfinite(abs(result.i0_pu))
    assert np.isfinite(abs(result.i1_pu))
    assert np.isfinite(abs(result.i2_pu))
    assert all(np.isfinite(np.abs(result.post_va_pu)))
    assert all(np.isfinite(np.abs(result.post_vb_pu)))
    assert all(np.isfinite(np.abs(result.post_vc_pu)))
