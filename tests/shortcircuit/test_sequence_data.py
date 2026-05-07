from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from src.parser import parse_matpower_case
from src.powerflow.nr import solve_newton_raphson
from src.shortcircuit import analyze_fault, build_sequence_ybus, fault_diagnostic_rows


def _data_path(*parts: str) -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "raw" / Path(*parts)


def _prefault_case():
    case = parse_matpower_case(_data_path("small_cases", "case3_sample.m"))
    result = solve_newton_raphson(case, tolerance=1e-10, max_iterations=50)
    assert result.converged
    return case, result.voltages


def test_explicit_generator_sequence_impedance_changes_ground_fault_level() -> None:
    case, v_prefault = _prefault_case()
    base = analyze_fault(case, v_prefault, fault_bus=2, fault_type="LG", default_gen_xdpp_pu=0.2)

    generators = [replace(case.generators[0], x1=0.6, x2=0.6, x0=0.6)]
    seq_case = replace(case, generators=generators)
    explicit = analyze_fault(seq_case, v_prefault, fault_bus=2, fault_type="LG", default_gen_xdpp_pu=0.2)

    assert abs(explicit.ia_pu) < abs(base.ia_pu)
    assert abs(explicit.fault_denominator_pu) > abs(base.fault_denominator_pu)


def test_generator_resistance_changes_fault_current_angle() -> None:
    case, v_prefault = _prefault_case()
    reactive = analyze_fault(case, v_prefault, fault_bus=2, fault_type="3PH", default_gen_xdpp_pu=0.2)

    generators = [replace(case.generators[0], r1=0.2, x1=0.2)]
    seq_case = replace(case, generators=generators)
    resistive = analyze_fault(seq_case, v_prefault, fault_bus=2, fault_type="3PH", default_gen_xdpp_pu=0.2)

    assert resistive.ia_pu != pytest.approx(reactive.ia_pu)


def test_explicit_branch_zero_sequence_overrides_scale_for_that_branch() -> None:
    case = parse_matpower_case(_data_path("small_cases", "case3_sample.m"))
    branches = [replace(case.branches[0], r0=0.5, x0=1.0), *case.branches[1:]]
    seq_case = replace(case, branches=branches)

    _y1_a, _y2_a, y0_a = build_sequence_ybus(seq_case, branch_zero_seq_scale=1.0)
    _y1_b, _y2_b, y0_b = build_sequence_ybus(seq_case, branch_zero_seq_scale=10.0)

    assert y0_a[0, 1] == pytest.approx(y0_b[0, 1])


def test_generator_mbase_conversion_changes_generator_admittance() -> None:
    case = parse_matpower_case(_data_path("small_cases", "case3_sample.m"))
    generators = [replace(case.generators[0], mbase=50.0, x1=0.2, x2=0.2, x0=0.2)]
    seq_case = replace(case, generators=generators)

    converted_y1, _converted_y2, _converted_y0 = build_sequence_ybus(
        seq_case,
        branch_zero_seq_scale=1.0,
        sequence_data_on_gen_mbase=True,
    )
    unconverted_y1, _unconverted_y2, _unconverted_y0 = build_sequence_ybus(
        seq_case,
        branch_zero_seq_scale=1.0,
        sequence_data_on_gen_mbase=False,
    )

    assert converted_y1[0, 0].imag > unconverted_y1[0, 0].imag


def test_fault_diagnostics_include_thevenin_and_slg_denominator() -> None:
    case, v_prefault = _prefault_case()
    result = analyze_fault(case, v_prefault, fault_bus=2, fault_type="LG")
    rows = fault_diagnostic_rows(result)
    quantities = {str(row["quantity"]) for row in rows}

    assert "Z0_th" in quantities
    assert "Z1_th" in quantities
    assert "Z2_th" in quantities
    assert "SLG denominator Z0+Z1+Z2+3Zf" in quantities
    assert all("method" in row for row in rows)
