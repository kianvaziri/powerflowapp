"""Generate final-submission validation artifacts for IEEE-14 demo."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from src.parser import parse_matpower_case
from src.powerflow.gs import solve_gauss_seidel
from src.powerflow.line_flow import compute_line_flows, compute_power_balance
from src.powerflow.nr import solve_newton_raphson
from src.shortcircuit import FAULT_TYPE_3PH, analyze_fault, fault_current_rows, post_fault_voltage_rows


def _write_csv(path: Path, rows: list[dict[str, float | int | str | bool]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _final_mismatch(result) -> float:
    if not result.history:
        return float("nan")
    return float(result.history[-1].max_power_mismatch)


def _solver_summary_rows(case, tolerance: float, max_iterations: int) -> list[dict[str, float | int | str | bool]]:
    rows: list[dict[str, float | int | str | bool]] = []
    methods = ["GS", "NR"]

    for method in methods:
        if method == "GS":
            result = solve_gauss_seidel(case, tolerance=tolerance, max_iterations=max_iterations)
        else:
            result = solve_newton_raphson(case, tolerance=tolerance, max_iterations=max_iterations)

        flows = compute_line_flows(case, result.voltages)
        balance = compute_power_balance(case, result.voltages, flows)
        vm = np.abs(result.voltages)

        rows.append(
            {
                "method": method,
                "converged": bool(result.converged),
                "iterations": int(result.iterations),
                "tolerance_pu": float(tolerance),
                "max_iterations": int(max_iterations),
                "final_max_mismatch_pu": _final_mismatch(result),
                "vm_min_pu": float(np.min(vm)),
                "vm_max_pu": float(np.max(vm)),
                "p_balance_mw": float(balance["p_balance_mw"]),
                "q_balance_mvar": float(balance["q_balance_mvar"]),
            }
        )

    return rows


def _choose_prefault_result(case, tolerance: float, max_iterations: int):
    nr_result = solve_newton_raphson(case, tolerance=tolerance, max_iterations=max_iterations)
    if nr_result.converged:
        return "NR", nr_result

    gs_result = solve_gauss_seidel(case, tolerance=tolerance, max_iterations=max_iterations)
    if gs_result.converged:
        return "GS", gs_result

    return "NR", nr_result


def run_demo(
    fault_bus: int = 4,
    zf_r: float = 0.0,
    zf_x: float = 0.0,
    tolerance: float = 1e-6,
    max_iterations: int = 200,
) -> dict[str, bool | int | float | str]:
    root = Path(__file__).resolve().parents[2]
    case_path = root / "data" / "raw" / "ieee14" / "case14_sample.m"
    out_dir = root / "docs" / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    case = parse_matpower_case(case_path)
    bus_ids = [bus.bus_i for bus in case.buses]
    if fault_bus not in bus_ids:
        fault_bus = bus_ids[0]

    powerflow_rows = _solver_summary_rows(case, tolerance=tolerance, max_iterations=max_iterations)

    prefault_method, prefault_result = _choose_prefault_result(case, tolerance=tolerance, max_iterations=max_iterations)
    zf = complex(zf_r, zf_x)
    fault_result = analyze_fault(
        case=case,
        pre_fault_voltages=prefault_result.voltages,
        fault_bus=fault_bus,
        fault_type=FAULT_TYPE_3PH,
        fault_impedance_pu=zf,
    )

    fault_current_table: list[dict[str, float | int | str | bool]] = []
    for row in fault_current_rows(fault_result):
        row_out = dict(row)
        row_out["fault_type"] = FAULT_TYPE_3PH
        row_out["fault_bus"] = fault_bus
        fault_current_table.append(row_out)

    fault_voltage_table: list[dict[str, float | int | str | bool]] = []
    for row in post_fault_voltage_rows(case, fault_result):
        row_out = dict(row)
        row_out["fault_type"] = FAULT_TYPE_3PH
        row_out["fault_bus"] = fault_bus
        fault_voltage_table.append(row_out)

    fault_summary_rows = [
        {
            "fault_type": FAULT_TYPE_3PH,
            "fault_bus": int(fault_bus),
            "zf_r_pu": float(zf.real),
            "zf_x_pu": float(zf.imag),
            "prefault_solver": prefault_method,
            "prefault_converged": bool(prefault_result.converged),
            "ia_mag_pu": float(abs(fault_result.ia_pu)),
            "ib_mag_pu": float(abs(fault_result.ib_pu)),
            "ic_mag_pu": float(abs(fault_result.ic_pu)),
        }
    ]

    _write_csv(out_dir / "final_ieee14_powerflow_summary.csv", powerflow_rows)
    _write_csv(out_dir / "final_ieee14_fault_summary.csv", fault_summary_rows)
    _write_csv(out_dir / "final_ieee14_fault_currents.csv", fault_current_table)
    _write_csv(out_dir / "final_ieee14_post_fault_voltages.csv", fault_voltage_table)

    gs_ok = any(r["method"] == "GS" and bool(r["converged"]) for r in powerflow_rows)
    nr_ok = any(r["method"] == "NR" and bool(r["converged"]) for r in powerflow_rows)
    tolerance_ok = tolerance <= 1e-6
    ia_ok = np.isfinite(abs(fault_result.ia_pu)) and abs(fault_result.ia_pu) > 0.0

    pass_all = bool(gs_ok and nr_ok and tolerance_ok and ia_ok and prefault_result.converged)

    summary_text = (
        "Final submission validation summary\n"
        f"Case: {case_path}\n"
        f"Tolerance (p.u.): {tolerance:.2e}\n"
        f"Max iterations: {max_iterations}\n"
        f"GS converged: {gs_ok}\n"
        f"NR converged: {nr_ok}\n"
        f"Prefault method used for fault demo: {prefault_method}\n"
        f"Prefault converged: {prefault_result.converged}\n"
        f"3PH fault bus: {fault_bus}\n"
        f"3PH |Ia| (p.u.): {abs(fault_result.ia_pu):.6f}\n"
        f"Reasonable tolerance check (<=1e-6): {tolerance_ok}\n"
        f"Overall status: {'PASS' if pass_all else 'CHECK REQUIRED'}\n"
    )
    (out_dir / "final_submission_summary.txt").write_text(summary_text, encoding="utf-8")

    print("Final demo complete")
    print(f"GS converged: {gs_ok}")
    print(f"NR converged: {nr_ok}")
    print(f"Fault bus: {fault_bus}")
    print(f"3PH |Ia| (p.u.): {abs(fault_result.ia_pu):.6f}")
    print(f"Overall status: {'PASS' if pass_all else 'CHECK REQUIRED'}")
    print(f"Artifacts written under: {out_dir}")

    return {
        "gs_converged": gs_ok,
        "nr_converged": nr_ok,
        "fault_bus": int(fault_bus),
        "ia_mag_pu": float(abs(fault_result.ia_pu)),
        "pass_all": pass_all,
        "tolerance_pu": float(tolerance),
    }


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate final submission validation artifacts")
    parser.add_argument("--fault-bus", type=int, default=4)
    parser.add_argument("--zf-r", type=float, default=0.0)
    parser.add_argument("--zf-x", type=float, default=0.0)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument("--max-iterations", type=int, default=200)
    return parser


if __name__ == "__main__":
    args = _arg_parser().parse_args()
    run_demo(
        fault_bus=args.fault_bus,
        zf_r=args.zf_r,
        zf_x=args.zf_x,
        tolerance=args.tolerance,
        max_iterations=args.max_iterations,
    )
