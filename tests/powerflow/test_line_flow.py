from __future__ import annotations

from pathlib import Path

import pytest

from src.parser import parse_matpower_case
from src.powerflow.gs import solve_gauss_seidel
from src.powerflow.line_flow import compute_line_flows, compute_power_balance
from src.powerflow.nr import solve_newton_raphson


def _data_path(*parts: str) -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "raw" / Path(*parts)


def test_line_flows_are_zero_for_flat_zero_injection_case() -> None:
    case = parse_matpower_case(_data_path("small_cases", "case3_sample.m"))
    result = solve_gauss_seidel(case, tolerance=1e-10, max_iterations=30)

    flows = compute_line_flows(case, result.voltages)

    assert len(flows) == 3
    for flow in flows:
        assert flow.p_from_mw == pytest.approx(0.0, abs=1e-12)
        assert flow.q_from_mvar == pytest.approx(0.0, abs=1e-12)
        assert flow.p_to_mw == pytest.approx(0.0, abs=1e-12)
        assert flow.q_to_mvar == pytest.approx(0.0, abs=1e-12)
        assert flow.p_loss_mw == pytest.approx(0.0, abs=1e-12)
        assert flow.q_loss_mvar == pytest.approx(0.0, abs=1e-12)

    balance = compute_power_balance(case, result.voltages, flows)
    assert balance["p_balance_mw"] == pytest.approx(0.0, abs=1e-12)
    assert balance["q_balance_mvar"] == pytest.approx(0.0, abs=1e-12)


def test_line_flow_with_tap_and_shunt_has_expected_signs_and_balance() -> None:
    case = parse_matpower_case(_data_path("small_cases", "case2_tap_shunt_sample.m"))
    result = solve_gauss_seidel(case, tolerance=1e-10, max_iterations=50)

    flows = compute_line_flows(case, result.voltages)
    assert len(flows) == 1

    flow = flows[0]
    assert flow.from_bus == 1
    assert flow.to_bus == 2
    assert flow.p_loss_mw > 0.0
    assert flow.q_loss_mvar < 0.0

    balance = compute_power_balance(case, result.voltages, flows)
    assert balance["p_generation_sched_mw"] == pytest.approx(0.0, abs=1e-12)
    assert balance["q_generation_sched_mvar"] == pytest.approx(0.0, abs=1e-12)
    assert balance["p_balance_mw"] == pytest.approx(0.0, abs=1e-10)
    assert balance["q_balance_mvar"] == pytest.approx(0.0, abs=1e-10)


def test_line_flow_and_balance_on_ieee14_nr_solution() -> None:
    case = parse_matpower_case(_data_path("ieee14", "case14_sample.m"))
    result = solve_newton_raphson(case, tolerance=1e-6, max_iterations=50)

    assert result.converged

    flows = compute_line_flows(case, result.voltages)
    assert len(flows) == 20
    assert sum(flow.p_loss_mw for flow in flows) > 0.0

    balance = compute_power_balance(case, result.voltages, flows)
    assert balance["q_bus_shunt_injection_mvar"] < 0.0
    assert balance["p_balance_mw"] == pytest.approx(0.0, abs=1e-8)
    assert balance["q_balance_mvar"] == pytest.approx(0.0, abs=1e-8)
