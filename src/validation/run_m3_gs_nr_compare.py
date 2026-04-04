"""Run M3 GS-vs-NR comparison and export summary CSV."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from src.parser import parse_matpower_case
from src.powerflow.gs import solve_gauss_seidel
from src.powerflow.nr import solve_newton_raphson


def _final_mismatch(history: list[object], attr: str) -> float:
    if not history:
        return 0.0
    return float(getattr(history[-1], attr))


def run_comparison(
    case_path: Path | None = None,
    output_path: Path | None = None,
    tolerance: float = 1e-6,
) -> Path:
    case_file = case_path or (Path(__file__).resolve().parents[2] / "data" / "raw" / "ieee14" / "case14_sample.m")
    output_file = output_path or (Path(__file__).resolve().parents[2] / "docs" / "validation" / "m3_gs_vs_nr_comparison.csv")

    case = parse_matpower_case(case_file)

    t0 = time.perf_counter()
    gs = solve_gauss_seidel(case, tolerance=tolerance, max_iterations=500)
    gs_ms = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    nr = solve_newton_raphson(case, tolerance=tolerance, max_iterations=50)
    nr_ms = (time.perf_counter() - t1) * 1000.0

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["method", "converged", "iterations", "elapsed_ms", "final_max_mismatch"])
        writer.writerow(["GS", gs.converged, gs.iterations, f"{gs_ms:.6f}", f"{_final_mismatch(gs.history, 'max_power_mismatch'):.12e}"])
        writer.writerow(["NR", nr.converged, nr.iterations, f"{nr_ms:.6f}", f"{_final_mismatch(nr.history, 'max_power_mismatch'):.12e}"])

    print(f"Comparison CSV written: {output_file}")
    print(f"GS: converged={gs.converged}, iter={gs.iterations}, elapsed_ms={gs_ms:.3f}")
    print(f"NR: converged={nr.converged}, iter={nr.iterations}, elapsed_ms={nr_ms:.3f}")

    return output_file


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run GS-vs-NR comparison")
    parser.add_argument("--case", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    run_comparison(case_path=args.case, output_path=args.output, tolerance=args.tolerance)
