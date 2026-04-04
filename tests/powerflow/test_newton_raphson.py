from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.parser import parse_matpower_case
from src.powerflow.nr import solve_newton_raphson


def test_nr_converges_on_zero_load_case3() -> None:
    case_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "small_cases" / "case3_sample.m"
    case = parse_matpower_case(case_path)

    result = solve_newton_raphson(case, tolerance=1e-10, max_iterations=20)

    assert result.converged
    assert result.iterations <= 20
    assert np.isclose(result.voltages[0].real, 1.0, atol=1e-12)
    assert np.isclose(result.voltages[0].imag, 0.0, atol=1e-12)


def test_nr_handles_slack_pv_pq_and_enforces_pv_magnitude() -> None:
    case_path = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "raw"
        / "small_cases"
        / "case3_gs_pv_sample.m"
    )
    case = parse_matpower_case(case_path)

    result = solve_newton_raphson(case, tolerance=1e-6, max_iterations=40)

    assert result.converged
    # Bus 2 is PV with specified |V| = 1.02.
    assert np.isclose(abs(result.voltages[1]), 1.02, atol=1e-4)

    if result.history:
        # Jacobian size should match number of state equations.
        assert result.history[-1].jacobian_size == 3


def test_nr_rejects_invalid_solver_parameters() -> None:
    case_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "small_cases" / "case3_sample.m"
    case = parse_matpower_case(case_path)

    with pytest.raises(ValueError, match="tolerance must be positive"):
        solve_newton_raphson(case, tolerance=0.0, max_iterations=10)

    with pytest.raises(ValueError, match="max_iterations must be positive"):
        solve_newton_raphson(case, tolerance=1e-6, max_iterations=0)
