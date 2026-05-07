from __future__ import annotations

from pathlib import Path

import pytest

from src.parser import parse_matpower_case


def test_parse_optional_sequence_sections(tmp_path) -> None:
    case_file = tmp_path / "case_with_sequence.m"
    case_file.write_text(
        """
mpc.baseMVA = 100;
mpc.bus = [
    1 3 0 0 0 0 1 1.0 0 138 1 1.1 0.9;
    2 1 0 0 0 0 1 1.0 0 138 1 1.1 0.9;
];
mpc.gen = [
    1 0 0 10 -10 1.0 50 1 100 0;
];
mpc.branch = [
    1 2 0.01 0.10 0.02 0 0 0 0 0 1 -360 360;
];
mpc.bus_seq = [
    2 0.01 -0.02 0.03 -0.04 0.05 -0.06;
];
mpc.gen_seq = [
    1 0.01 0.20 0.02 0.25 0.03 0.30 0.04 0.05;
];
mpc.branch_seq = [
    1 2 0.02 0.11 0.01 0.05 0.30 0.00 1;
];
""",
        encoding="utf-8",
    )

    case = parse_matpower_case(case_file)

    assert case.base_mva == pytest.approx(100.0)
    assert case.buses[1].seq_g1 == pytest.approx(0.01)
    assert case.buses[1].seq_b0 == pytest.approx(-0.06)
    assert case.generators[0].mbase == pytest.approx(50.0)
    assert case.generators[0].r1 == pytest.approx(0.01)
    assert case.generators[0].x2 == pytest.approx(0.25)
    assert case.generators[0].r0 == pytest.approx(0.03)
    assert case.generators[0].xn == pytest.approx(0.05)
    assert case.branches[0].r2 == pytest.approx(0.02)
    assert case.branches[0].x0 == pytest.approx(0.30)
    assert case.branches[0].zero_sequence_status == 1


def test_parse_minimal_sequence_rows(tmp_path) -> None:
    case_file = tmp_path / "case_with_minimal_sequence.m"
    case_file.write_text(
        """
mpc.baseMVA = 100;
mpc.bus = [
    1 3 0 0 0 0 1 1.0 0 138 1 1.1 0.9;
    2 1 0 0 0 0 1 1.0 0 138 1 1.1 0.9;
];
mpc.gen = [
    1 0 0 10 -10 1.0 100 1 100 0;
];
mpc.branch = [
    1 2 0.01 0.10 0.02 0 0 0 0 0 1 -360 360;
];
mpc.gen_seq = [
    1 0.20 0.25 0.30;
];
mpc.branch_seq = [
    1 2 0.05 0.30 0.00 0;
];
""",
        encoding="utf-8",
    )

    case = parse_matpower_case(case_file)

    assert case.generators[0].r1 is None
    assert case.generators[0].x1 == pytest.approx(0.20)
    assert case.generators[0].x0 == pytest.approx(0.30)
    assert case.branches[0].r0 == pytest.approx(0.05)
    assert case.branches[0].x0 == pytest.approx(0.30)
    assert case.branches[0].zero_sequence_status == 0


def test_ieee14_powerworld_sequence_template_parses() -> None:
    case_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "ieee14" / "case14_powerworld_sequence_template.m"

    case = parse_matpower_case(case_path)

    assert len(case.buses) == 14
    assert len(case.generators) == 5
    assert len(case.branches) == 20
    assert case.generators[0].x1 == pytest.approx(0.2)
    assert case.branches[0].r0 == pytest.approx(2.5 * case.branches[0].r)

def test_ieee14_literature_sequence_case_parses() -> None:
    case_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "ieee14" / "case14_literature_sequence.m"

    case = parse_matpower_case(case_path)

    assert len(case.buses) == 14
    assert len(case.generators) == 5
    assert len(case.branches) == 20
    assert case.generators[0].x1 == pytest.approx(0.007)
    assert case.branches[7].x0 == pytest.approx(0.048)

