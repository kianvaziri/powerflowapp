from __future__ import annotations

from src.models import Branch, Bus, Generator, PowerSystemCase
from src.validation import has_validation_errors, validate_case_data


def _base_case() -> PowerSystemCase:
    buses = [
        Bus(1, 3, 0.0, 0.0, 0.0, 0.0, 1, 1.0, 0.0, 230.0, 1, 1.1, 0.9),
        Bus(2, 1, 0.0, 0.0, 0.0, 0.0, 1, 1.0, 0.0, 230.0, 1, 1.1, 0.9),
    ]
    generators = [
        Generator(1, 0.0, 0.0, 10.0, -10.0, 1.0, 100.0, 1, 10.0, 0.0),
    ]
    branches = [
        Branch(1, 2, 0.1, 0.2, 0.0, 0.0, 0.0, 1),
    ]
    return PowerSystemCase(base_mva=100.0, buses=buses, generators=generators, branches=branches)


def test_validate_case_data_accepts_minimal_valid_case() -> None:
    case = _base_case()
    findings = validate_case_data(case)
    assert not has_validation_errors(findings)


def test_validate_case_data_catches_missing_slack_and_zero_impedance() -> None:
    case = _base_case()
    case = PowerSystemCase(
        base_mva=case.base_mva,
        buses=[
            Bus(1, 1, 0.0, 0.0, 0.0, 0.0, 1, 1.0, 0.0, 230.0, 1, 1.1, 0.9),
            Bus(2, 1, 0.0, 0.0, 0.0, 0.0, 1, 1.0, 0.0, 230.0, 1, 1.1, 0.9),
        ],
        generators=case.generators,
        branches=[Branch(1, 2, 0.0, 0.0, 0.0, 0.0, 0.0, 1)],
    )

    findings = validate_case_data(case)
    codes = {f.code for f in findings}

    assert "MISSING_SLACK_BUS" in codes
    assert "ZERO_BRANCH_IMPEDANCE" in codes
    assert has_validation_errors(findings)


def test_validate_case_data_catches_duplicate_branch_and_bad_generator_limits() -> None:
    case = _base_case()
    case = PowerSystemCase(
        base_mva=case.base_mva,
        buses=case.buses,
        generators=[
            Generator(1, 0.0, 0.0, 10.0, -10.0, 1.0, 100.0, 1, 10.0, 0.0),
            Generator(2, 0.0, 0.0, -1.0, 2.0, 1.0, 100.0, 1, 1.0, 2.0),
        ],
        branches=[
            Branch(1, 2, 0.1, 0.2, 0.0, 0.0, 0.0, 1),
            Branch(2, 1, 0.1, 0.2, 0.0, 0.0, 0.0, 1),
        ],
    )

    findings = validate_case_data(case)
    codes = {f.code for f in findings}

    assert "DUPLICATE_BRANCH" in codes
    assert "INCONSISTENT_P_LIMITS" in codes
    assert "INCONSISTENT_Q_LIMITS" in codes
