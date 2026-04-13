"""Milestone 4/5 Streamlit UI for solver execution and reporting/export."""

from __future__ import annotations

import csv
import io
import tempfile
from dataclasses import asdict
from pathlib import Path

import numpy as np
import streamlit as st

from src.parser import parse_matpower_case
from src.powerflow.gs import solve_gauss_seidel
from src.powerflow.line_flow import compute_line_flows, compute_power_balance
from src.powerflow.nr import solve_newton_raphson
from src.shortcircuit import analyze_fault, fault_current_rows, post_fault_voltage_rows


def _default_case_options() -> dict[str, Path]:
    root = Path(__file__).resolve().parents[2]
    return {
        "IEEE 14-bus": root / "data" / "raw" / "ieee14" / "case14_sample.m",
        "3-bus baseline": root / "data" / "raw" / "small_cases" / "case3_sample.m",
        "3-bus PV example": root / "data" / "raw" / "small_cases" / "case3_gs_pv_sample.m",
    }


def _fault_type_options() -> dict[str, str]:
    return {
        "Three-phase (3PH)": "3PH",
        "Line-to-Ground (LG)": "LG",
        "Line-to-Line (LL)": "LL",
        "Double-Line-to-Ground (LLG)": "LLG",
    }


def _uploaded_to_temp(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix or ".m"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def _bus_rows(case, voltages: np.ndarray) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    for idx, bus in enumerate(case.buses):
        v = voltages[idx]
        rows.append(
            {
                "bus": bus.bus_i,
                "type": bus.bus_type,
                "vm_pu": float(abs(v)),
                "va_deg": float(np.degrees(np.angle(v))),
                "pd_mw": float(bus.pd),
                "qd_mvar": float(bus.qd),
            }
        )
    return rows


def _line_rows(flows) -> list[dict[str, float | int]]:
    return [asdict(flow) for flow in flows]


def _history_rows(method: str, history) -> list[dict[str, float | int]]:
    if method == "GS":
        return [
            {
                "iteration": h.iteration,
                "max_voltage_change": h.max_voltage_change,
                "max_power_mismatch": h.max_power_mismatch,
            }
            for h in history
        ]

    return [
        {
            "iteration": h.iteration,
            "max_power_mismatch": h.max_power_mismatch,
            "max_state_update": h.max_state_update,
            "jacobian_size": h.jacobian_size,
        }
        for h in history
    ]


def _to_csv_bytes(rows: list[dict[str, float | int | str]]) -> bytes:
    if not rows:
        return b""

    with io.StringIO() as sio:
        writer = csv.DictWriter(sio, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return sio.getvalue().encode("utf-8")


def main() -> None:
    st.set_page_config(page_title="Power Flow App", layout="wide")
    st.title("EE 4310 Power Flow App (M4/M5)")
    st.caption(
        "Load a case file, run GS/NR, view line flows and short-circuit results, and export CSV/TXT reports."
    )

    options = _default_case_options()
    fault_type_map = _fault_type_options()

    st.sidebar.header("Inputs")
    selected_case_name = st.sidebar.selectbox("Select bundled case", list(options.keys()))
    uploaded_file = st.sidebar.file_uploader("Or upload MATPOWER-style .m file", type=["m", "txt"])

    method = st.sidebar.selectbox("Solver", ["GS", "NR"])
    tolerance = st.sidebar.number_input("Tolerance", min_value=1e-10, max_value=1.0, value=1e-6, format="%.1e")
    max_iterations = st.sidebar.number_input("Max iterations", min_value=1, max_value=5000, value=200, step=1)

    st.sidebar.header("Fault Analysis (M5)")
    fault_type_label = st.sidebar.selectbox("Fault type", list(fault_type_map.keys()))
    fault_type = fault_type_map[fault_type_label]
    fault_z_r = st.sidebar.number_input(
        "Fault impedance Rf (p.u.)",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=0.01,
        format="%.4f",
    )
    fault_z_x = st.sidebar.number_input(
        "Fault impedance Xf (p.u.)",
        min_value=-100.0,
        max_value=100.0,
        value=0.0,
        step=0.01,
        format="%.4f",
    )

    case_path = _uploaded_to_temp(uploaded_file) if uploaded_file is not None else options[selected_case_name]

    preview_case = None
    preview_error: str | None = None
    try:
        preview_case = parse_matpower_case(case_path)
    except Exception as exc:  # pylint: disable=broad-except
        preview_error = str(exc)

    fault_bus: int | None = None
    if preview_case is not None:
        bus_ids = [bus.bus_i for bus in preview_case.buses]
        fault_bus = st.sidebar.selectbox("Fault location", bus_ids, format_func=lambda b: f"Bus {b}")
    else:
        st.sidebar.warning("Provide a valid case file to choose fault location.")
        if preview_error is not None:
            st.sidebar.error(f"Case parse error: {preview_error}")

    run = st.sidebar.button("Run Analysis", type="primary")

    if not run:
        st.info("Choose settings in the sidebar, then click Run Analysis.")
        return

    try:
        if preview_case is None:
            raise ValueError("Could not parse case file. Check input format and try again.")
        if fault_bus is None:
            raise ValueError("Fault location is required for M5 analysis")

        case = preview_case

        if method == "GS":
            result = solve_gauss_seidel(case, tolerance=float(tolerance), max_iterations=int(max_iterations))
        else:
            result = solve_newton_raphson(case, tolerance=float(tolerance), max_iterations=int(max_iterations))

        voltages = result.voltages
        flows = compute_line_flows(case, voltages)
        balance = compute_power_balance(case, voltages, flows)

        fault_result = analyze_fault(
            case=case,
            pre_fault_voltages=voltages,
            fault_bus=int(fault_bus),
            fault_type=fault_type,
            fault_impedance_pu=complex(float(fault_z_r), float(fault_z_x)),
        )

        bus_rows = _bus_rows(case, voltages)
        line_rows = _line_rows(flows)
        history_rows = _history_rows(method, result.history)
        balance_rows = [balance]

        fault_current_table = fault_current_rows(fault_result)
        fault_voltage_table = post_fault_voltage_rows(case, fault_result)

        st.subheader("Run Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Solver", method)
        col2.metric("Converged", str(result.converged))
        col3.metric("Iterations", str(result.iterations))

        if not result.converged:
            st.warning("Solver did not converge at current settings. Results are shown for diagnosis.")

        st.subheader("Bus Voltages")
        st.dataframe(bus_rows, use_container_width=True)

        st.subheader("Line Flows and Losses")
        st.dataframe(line_rows, use_container_width=True)

        st.subheader("Power Balance")
        st.dataframe(balance_rows, use_container_width=True)

        st.subheader("Iteration History")
        st.dataframe(history_rows, use_container_width=True)

        st.subheader("Fault Analysis")
        f1, f2, f3 = st.columns(3)
        f1.metric("Fault Type", fault_result.fault_type)
        f2.metric("Fault Bus", f"Bus {fault_result.fault_bus}")
        f3.metric("|Ia| (p.u.)", f"{abs(fault_result.ia_pu):.6f}")

        st.markdown(
            f"Fault impedance Zf (p.u.): `{fault_result.fault_impedance_pu.real:.4f} + j{fault_result.fault_impedance_pu.imag:.4f}`"
        )

        st.markdown("**Fault Currents (Sequence + Phase)**")
        st.dataframe(fault_current_table, use_container_width=True)

        st.markdown("**Post-Fault Bus Voltages (Phase Domain)**")
        st.dataframe(fault_voltage_table, use_container_width=True)

        st.subheader("Export")
        st.download_button(
            "Download bus_results.csv",
            data=_to_csv_bytes(bus_rows),
            file_name="bus_results.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download line_flows.csv",
            data=_to_csv_bytes(line_rows),
            file_name="line_flows.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download iteration_history.csv",
            data=_to_csv_bytes(history_rows),
            file_name="iteration_history.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download power_balance.csv",
            data=_to_csv_bytes(balance_rows),
            file_name="power_balance.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download fault_currents.csv",
            data=_to_csv_bytes(fault_current_table),
            file_name="fault_currents.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download post_fault_voltages.csv",
            data=_to_csv_bytes(fault_voltage_table),
            file_name="post_fault_voltages.csv",
            mime="text/csv",
        )

        txt_summary = (
            f"Solver: {method}\n"
            f"Converged: {result.converged}\n"
            f"Iterations: {result.iterations}\n"
            f"Fault type: {fault_result.fault_type}\n"
            f"Fault bus: {fault_result.fault_bus}\n"
            f"Fault Zf (p.u.): {fault_result.fault_impedance_pu.real:.6f} + j{fault_result.fault_impedance_pu.imag:.6f}\n"
            f"|Ia| (p.u.): {abs(fault_result.ia_pu):.6e}\n"
            f"P balance (MW): {balance['p_balance_mw']:.6e}\n"
            f"Q balance (MVAr): {balance['q_balance_mvar']:.6e}\n"
        )
        st.download_button(
            "Download summary.txt",
            data=txt_summary.encode("utf-8"),
            file_name="summary.txt",
            mime="text/plain",
        )

    except Exception as exc:  # pylint: disable=broad-except
        st.error(f"Run failed: {exc}")


if __name__ == "__main__":
    main()
