"""Generate M4 CSV artifacts (bus, line, history, balance) for documentation."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from pathlib import Path

import numpy as np

from src.parser import parse_matpower_case
from src.powerflow.gs import solve_gauss_seidel
from src.powerflow.line_flow import compute_line_flows, compute_power_balance
from src.powerflow.nr import solve_newton_raphson


def _write_csv(path: Path, rows: list[dict[str, float | int]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_demo(method: str = "NR", tolerance: float = 1e-6, max_iterations: int = 200) -> None:
    root = Path(__file__).resolve().parents[2]
    case_path = root / "data" / "raw" / "ieee14" / "case14_sample.m"
    out_dir = root / "docs" / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    case = parse_matpower_case(case_path)
    method_upper = method.upper()
    if method_upper == "GS":
        result = solve_gauss_seidel(case, tolerance=tolerance, max_iterations=max_iterations)
    else:
        result = solve_newton_raphson(case, tolerance=tolerance, max_iterations=max_iterations)

    voltages = result.voltages
    flows = compute_line_flows(case, voltages)
    balance = compute_power_balance(case, voltages, flows)

    bus_rows: list[dict[str, float | int]] = []
    for i, bus in enumerate(case.buses):
        bus_rows.append(
            {
                "bus": bus.bus_i,
                "type": bus.bus_type,
                "vm_pu": float(abs(voltages[i])),
                "va_deg": float(np.degrees(np.angle(voltages[i]))),
                "pd_mw": float(bus.pd),
                "qd_mvar": float(bus.qd),
            }
        )

    line_rows = [asdict(flow) for flow in flows]

    if method_upper == "GS":
        history_rows: list[dict[str, float | int]] = [
            {
                "iteration": h.iteration,
                "max_voltage_change": h.max_voltage_change,
                "max_power_mismatch": h.max_power_mismatch,
            }
            for h in result.history
        ]
    else:
        history_rows = [
            {
                "iteration": h.iteration,
                "max_power_mismatch": h.max_power_mismatch,
                "max_state_update": h.max_state_update,
                "jacobian_size": h.jacobian_size,
            }
            for h in result.history
        ]

    balance_rows = [balance]

    _write_csv(out_dir / f"m4_{method_upper.lower()}_bus_results.csv", bus_rows)
    _write_csv(out_dir / f"m4_{method_upper.lower()}_line_flows.csv", line_rows)
    _write_csv(out_dir / f"m4_{method_upper.lower()}_iteration_history.csv", history_rows)
    _write_csv(out_dir / f"m4_{method_upper.lower()}_power_balance.csv", balance_rows)

    print(f"M4 {method_upper} demo complete")
    print(f"Converged: {result.converged}")
    print(f"Iterations: {result.iterations}")
    print(f"P balance (MW): {balance['p_balance_mw']:.6e}")
    print(f"Q balance (MVAr): {balance['q_balance_mvar']:.6e}")
    print(f"Artifacts written under: {out_dir}")


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate M4 line-flow/export artifacts")
    parser.add_argument("--method", type=str, default="NR", choices=["GS", "NR", "gs", "nr"])
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument("--max-iterations", type=int, default=200)
    return parser


if __name__ == "__main__":
    args = _arg_parser().parse_args()
    run_demo(method=args.method, tolerance=args.tolerance, max_iterations=args.max_iterations)
