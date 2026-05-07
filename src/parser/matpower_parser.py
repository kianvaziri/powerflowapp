"""Parser for MATPOWER-style plain-text case files used by GridSolver."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from src.models import Branch, Bus, Generator, PowerSystemCase

_NUMBER_PATTERN = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def parse_matpower_case(file_path: str | Path) -> PowerSystemCase:
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")

    base_mva = _parse_base_mva(text)
    bus_rows = _extract_matrix_rows(text, "bus")
    gen_rows = _extract_matrix_rows(text, "gen")
    branch_rows = _extract_matrix_rows(text, "branch")

    buses = [_row_to_bus(row, idx) for idx, row in enumerate(bus_rows, start=1)]
    generators = [_row_to_generator(row, idx) for idx, row in enumerate(gen_rows, start=1)]
    branches = [_row_to_branch(row, idx) for idx, row in enumerate(branch_rows, start=1)]

    buses = _apply_bus_sequence(buses, _extract_matrix_rows(text, "bus_seq", required=False))
    generators = _apply_generator_sequence(
        generators,
        _extract_matrix_rows(text, "gen_seq", required=False),
    )
    branches = _apply_branch_sequence(
        branches,
        _extract_matrix_rows(text, "branch_seq", required=False),
    )

    return PowerSystemCase(
        base_mva=base_mva,
        buses=buses,
        generators=generators,
        branches=branches,
    )


def _parse_base_mva(text: str) -> float:
    match = re.search(rf"mpc\.baseMVA\s*=\s*({_NUMBER_PATTERN})\s*;", text)
    if not match:
        return 100.0
    return float(match.group(1))


def _extract_matrix_rows(text: str, section: str, required: bool = True) -> list[list[float]]:
    pattern = rf"mpc\.{re.escape(section)}\s*=\s*\[(.*?)\];"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        if required:
            raise ValueError(f"Missing required section: mpc.{section}")
        return []

    block = match.group(1)
    rows: list[list[float]] = []
    for line_no, raw_line in enumerate(block.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        line = line.split("%", maxsplit=1)[0].strip()
        if not line:
            continue
        if line.endswith(";"):
            line = line[:-1].strip()
        if not line:
            continue

        try:
            values = [float(token) for token in line.split()]
        except ValueError as exc:
            raise ValueError(
                f"Could not parse numeric row in mpc.{section} at block line {line_no}: {raw_line}"
            ) from exc
        rows.append(values)

    if not rows and required:
        raise ValueError(f"Section mpc.{section} is empty")
    return rows


def _row_to_bus(row: list[float], idx: int) -> Bus:
    if len(row) < 13:
        raise ValueError(f"Bus row {idx} has {len(row)} columns; expected >= 13")
    return Bus(
        bus_i=int(row[0]),
        bus_type=int(row[1]),
        pd=row[2],
        qd=row[3],
        gs=row[4],
        bs=row[5],
        area=int(row[6]),
        vm=row[7],
        va=row[8],
        base_kv=row[9],
        zone=int(row[10]),
        vmax=row[11],
        vmin=row[12],
    )


def _row_to_generator(row: list[float], idx: int) -> Generator:
    if len(row) < 10:
        raise ValueError(f"Generator row {idx} has {len(row)} columns; expected >= 10")
    return Generator(
        bus=int(row[0]),
        pg=row[1],
        qg=row[2],
        qmax=row[3],
        qmin=row[4],
        vg=row[5],
        mbase=row[6],
        status=int(row[7]),
        pmax=row[8],
        pmin=row[9],
    )


def _row_to_branch(row: list[float], idx: int) -> Branch:
    if len(row) < 13:
        raise ValueError(f"Branch row {idx} has {len(row)} columns; expected >= 13")
    return Branch(
        fbus=int(row[0]),
        tbus=int(row[1]),
        r=row[2],
        x=row[3],
        b=row[4],
        ratio=row[8],
        angle=row[9],
        status=int(row[10]),
    )


def _apply_bus_sequence(buses: list[Bus], rows: list[list[float]]) -> list[Bus]:
    if not rows:
        return buses

    bus_by_id = {bus.bus_i: idx for idx, bus in enumerate(buses)}
    updated = list(buses)
    for row_idx, row in enumerate(rows, start=1):
        if len(row) < 7:
            raise ValueError(
                f"Bus sequence row {row_idx} has {len(row)} columns; expected bus g1 b1 g2 b2 g0 b0"
            )
        bus_id = int(row[0])
        if bus_id not in bus_by_id:
            raise ValueError(f"Bus sequence row {row_idx} references unknown bus {bus_id}")
        idx = bus_by_id[bus_id]
        updated[idx] = replace(
            updated[idx],
            seq_g1=row[1],
            seq_b1=row[2],
            seq_g2=row[3],
            seq_b2=row[4],
            seq_g0=row[5],
            seq_b0=row[6],
        )
    return updated


def _apply_generator_sequence(generators: list[Generator], rows: list[list[float]]) -> list[Generator]:
    if not rows:
        return generators

    updated = list(generators)
    for row_idx, row in enumerate(rows, start=1):
        if len(row) == 4:
            updates = {
                "x1": row[1],
                "x2": row[2],
                "x0": row[3],
            }
        elif len(row) in (7, 9):
            updates = {
                "r1": row[1],
                "x1": row[2],
                "r2": row[3],
                "x2": row[4],
                "r0": row[5],
                "x0": row[6],
            }
            if len(row) == 9:
                updates["rn"] = row[7]
                updates["xn"] = row[8]
        else:
            raise ValueError(
                f"Generator sequence row {row_idx} has {len(row)} columns; "
                "expected bus x1 x2 x0 or bus r1 x1 r2 x2 r0 x0 [rn xn]"
            )

        bus_id = int(row[0])
        matched = False
        for gen_idx, gen in enumerate(updated):
            if gen.bus == bus_id:
                updated[gen_idx] = replace(gen, **updates)
                matched = True
        if not matched:
            raise ValueError(f"Generator sequence row {row_idx} references unknown generator bus {bus_id}")
    return updated


def _apply_branch_sequence(branches: list[Branch], rows: list[list[float]]) -> list[Branch]:
    if not rows:
        return branches

    updated = list(branches)
    for row_idx, row in enumerate(rows, start=1):
        if len(row) == 9:
            updates = {
                "r2": row[2],
                "x2": row[3],
                "b2": row[4],
                "r0": row[5],
                "x0": row[6],
                "b0": row[7],
                "zero_sequence_status": int(row[8]),
            }
        elif len(row) in (4, 5, 6):
            updates = {
                "r0": row[2],
                "x0": row[3],
            }
            if len(row) >= 5:
                updates["b0"] = row[4]
            if len(row) == 6:
                updates["zero_sequence_status"] = int(row[5])
        else:
            raise ValueError(
                f"Branch sequence row {row_idx} has {len(row)} columns; "
                "expected fbus tbus r0 x0 [b0 status] or fbus tbus r2 x2 b2 r0 x0 b0 status"
            )

        fbus = int(row[0])
        tbus = int(row[1])
        exact_matches = [idx for idx, br in enumerate(updated) if br.fbus == fbus and br.tbus == tbus]
        matches = exact_matches or [idx for idx, br in enumerate(updated) if br.fbus == tbus and br.tbus == fbus]
        if not matches:
            raise ValueError(f"Branch sequence row {row_idx} references unknown branch {fbus}-{tbus}")

        for branch_idx in matches:
            updated[branch_idx] = replace(updated[branch_idx], **updates)
    return updated
