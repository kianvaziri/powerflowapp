"""Generate M5 short-circuit validation artifacts."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.parser import parse_matpower_case
from src.powerflow.gs import solve_gauss_seidel
from src.powerflow.nr import solve_newton_raphson
from src.shortcircuit import (
    FAULT_TYPE_3PH,
    FAULT_TYPE_LG,
    FAULT_TYPE_LL,
    FAULT_TYPE_LLG,
    analyze_fault,
    fault_current_rows,
    post_fault_voltage_rows,
)


def _write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_demo(
    method: str = "NR",
    fault_bus: int = 1,
    zf_r: float = 0.0,
    zf_x: float = 0.0,
    tolerance: float = 1e-6,
    max_iterations: int = 200,
) -> None:
    root = Path(__file__).resolve().parents[2]
    case_path = root / "data" / "raw" / "ieee14" / "case14_sample.m"
    out_dir = root / "docs" / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    case = parse_matpower_case(case_path)
    bus_ids = [bus.bus_i for bus in case.buses]
    if fault_bus not in bus_ids:
        fault_bus = bus_ids[0]

    method_upper = method.upper()
    if method_upper == "GS":
        result = solve_gauss_seidel(case, tolerance=tolerance, max_iterations=max_iterations)
    else:
        result = solve_newton_raphson(case, tolerance=tolerance, max_iterations=max_iterations)

    pre_fault_v = result.voltages
    zf = complex(zf_r, zf_x)

    fault_types = [FAULT_TYPE_3PH, FAULT_TYPE_LG, FAULT_TYPE_LL, FAULT_TYPE_LLG]

    current_rows: list[dict[str, float | int | str]] = []
    voltage_rows: list[dict[str, float | int | str]] = []

    for fault_type in fault_types:
        fault_result = analyze_fault(
            case=case,
            pre_fault_voltages=pre_fault_v,
            fault_bus=fault_bus,
            fault_type=fault_type,
            fault_impedance_pu=zf,
        )

        for row in fault_current_rows(fault_result):
            row_with_type = dict(row)
            row_with_type["fault_type"] = fault_type
            row_with_type["fault_bus"] = fault_bus
            current_rows.append(row_with_type)

        for row in post_fault_voltage_rows(case, fault_result):
            row_with_type = dict(row)
            row_with_type["fault_type"] = fault_type
            row_with_type["fault_bus"] = fault_bus
            voltage_rows.append(row_with_type)

    _write_csv(out_dir / f"m5_{method_upper.lower()}_fault_currents.csv", current_rows)
    _write_csv(out_dir / f"m5_{method_upper.lower()}_post_fault_voltages.csv", voltage_rows)

    print(f"M5 {method_upper} demo complete")
    print(f"Pre-fault converged: {result.converged}")
    print(f"Pre-fault iterations: {result.iterations}")
    print(f"Fault bus: {fault_bus}")
    print(f"Fault impedance Zf (p.u.): {zf_r:.4f} + j{zf_x:.4f}")
    print(f"Artifacts written under: {out_dir}")


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate M5 short-circuit validation artifacts")
    parser.add_argument("--method", type=str, default="NR", choices=["GS", "NR", "gs", "nr"])
    parser.add_argument("--fault-bus", type=int, default=1)
    parser.add_argument("--zf-r", type=float, default=0.0)
    parser.add_argument("--zf-x", type=float, default=0.0)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument("--max-iterations", type=int, default=200)
    return parser


if __name__ == "__main__":
    args = _arg_parser().parse_args()
    run_demo(
        method=args.method,
        fault_bus=args.fault_bus,
        zf_r=args.zf_r,
        zf_x=args.zf_x,
        tolerance=args.tolerance,
        max_iterations=args.max_iterations,
    )
