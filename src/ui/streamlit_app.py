"""Workflow-driven Streamlit UI for power flow and fault studies."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import tempfile
from datetime import datetime
from dataclasses import asdict
from pathlib import Path

import numpy as np
import streamlit as st

from src.parser import parse_matpower_case
from src.powerflow.gs import solve_gauss_seidel
from src.powerflow.line_flow import compute_line_flows, compute_power_balance
from src.powerflow.nr import solve_newton_raphson
from src.shortcircuit import analyze_fault, fault_current_rows, post_fault_voltage_rows
from src.validation import has_validation_errors, validate_case_data
from src.ybus import build_ybus


def _default_case_options() -> dict[str, Path]:
    root = Path(__file__).resolve().parents[2]
    return {
        "IEEE 14-bus": root / "data" / "raw" / "ieee14" / "case14_sample.m",
        "3-bus baseline": root / "data" / "raw" / "small_cases" / "case3_sample.m",
        "3-bus PV example": root / "data" / "raw" / "small_cases" / "case3_gs_pv_sample.m",
    }


def _fault_type_options() -> dict[str, str]:
    return {
        "3PH": "3PH",
        "SLG": "LG",
        "DLG": "LLG",
        "LL": "LL",
    }


def _uploaded_to_temp(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix or ".m"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def _selected_source_signature(selected_case_name: str, uploaded_file) -> str:
    if uploaded_file is None:
        return f"bundled::{selected_case_name}"

    payload = uploaded_file.getvalue()
    digest = hashlib.sha256(payload).hexdigest()[:16]
    return f"upload::{uploaded_file.name}::{len(payload)}::{digest}"


def _load_case_from_selection(options: dict[str, Path], selected_case_name: str, uploaded_file):
    case_path = _uploaded_to_temp(uploaded_file) if uploaded_file is not None else options[selected_case_name]
    label = uploaded_file.name if uploaded_file is not None else selected_case_name
    loaded_case = parse_matpower_case(case_path)
    source_signature = _selected_source_signature(selected_case_name, uploaded_file)
    return loaded_case, label, source_signature


def _apply_theme_css(dark_mode: bool) -> None:
    if dark_mode:
        css = """
        <style>
        .stApp { background-color: #0e1117; color: #e6edf3; }
        [data-testid="stSidebar"] { background-color: #161b22; }
        [data-testid="stMetricValue"] { color: #e6edf3; }
        .workflow-step { padding: 0.25rem 0.4rem; border-radius: 0.4rem; background: #1f2937; }
        div.stButton > button {
            width: 100%;
            min-height: 3.15rem;
            border-radius: 0.75rem;
            border: 1px solid #2f3947;
            background: #1f2937;
            color: #e6edf3;
            font-family: Calibri, "Segoe UI", sans-serif;
            font-size: 0.98rem;
            font-weight: 650;
            letter-spacing: 0.01em;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
            transition: all 0.18s ease;
        }
        div.stButton > button:hover:not(:disabled) {
            background: #273244;
            border-color: #475569;
        }
        div.stButton > button:active:not(:disabled) {
            transform: translateY(1px);
        }
        div.stButton > button:focus {
            outline: none;
            box-shadow: 0 0 0 0.2rem rgba(59, 130, 246, 0.35);
        }
        div.stButton > button[kind="primary"] {
            background: #2563eb;
            color: #ffffff;
            border-color: #1d4ed8;
        }
        div.stButton > button[kind="primary"]:hover:not(:disabled) {
            background: #1d4ed8;
            border-color: #1e40af;
        }
        div.stButton > button:disabled {
            background: #111827;
            color: #6b7280;
            border-color: #374151;
            opacity: 1;
            cursor: not-allowed;
            box-shadow: none;
        }
        div.stDownloadButton > button {
            border-radius: 0.65rem;
            min-height: 2.65rem;
            font-family: Calibri, "Segoe UI", sans-serif;
        }
        </style>
        """
    else:
        css = """
        <style>
        .stApp { background: linear-gradient(180deg, #f8fafc 0%, #ffffff 45%); color: #111827; }
        [data-testid="stSidebar"] { background-color: #f4f7fb; }
        [data-testid="stMetricValue"] { color: #111827; }
        .workflow-step { padding: 0.25rem 0.4rem; border-radius: 0.4rem; background: #f3f4f6; }
        div.stButton > button {
            width: 100%;
            min-height: 3.15rem;
            border-radius: 0.75rem;
            border: 1px solid #cbd5e1;
            background: #ffffff;
            color: #0f172a;
            font-family: Calibri, "Segoe UI", sans-serif;
            font-size: 0.98rem;
            font-weight: 650;
            letter-spacing: 0.01em;
            box-shadow: 0 1px 3px rgba(2, 6, 23, 0.1), 0 10px 20px rgba(2, 6, 23, 0.05);
            transition: all 0.18s ease;
        }
        div.stButton > button:hover:not(:disabled) {
            background: #f8fafc;
            border-color: #94a3b8;
            box-shadow: 0 4px 12px rgba(2, 6, 23, 0.14);
        }
        div.stButton > button:active:not(:disabled) {
            transform: translateY(1px);
        }
        div.stButton > button:focus {
            outline: none;
            box-shadow: 0 0 0 0.2rem rgba(37, 99, 235, 0.2);
        }
        div.stButton > button[kind="primary"] {
            background: #eff6ff;
            border-color: #93c5fd;
            color: #1d4ed8;
        }
        div.stButton > button[kind="primary"]:hover:not(:disabled) {
            background: #dbeafe;
            border-color: #60a5fa;
            color: #1e40af;
        }
        div.stButton > button:disabled {
            background: #f8fafc;
            color: #94a3b8;
            border-color: #e2e8f0;
            opacity: 1;
            cursor: not-allowed;
            box-shadow: none;
        }
        div.stDownloadButton > button {
            border-radius: 0.65rem;
            min-height: 2.65rem;
            border: 1px solid #cbd5e1;
            background: #ffffff;
            color: #0f172a;
            font-family: Calibri, "Segoe UI", sans-serif;
        }
        div.stDownloadButton > button:hover:not(:disabled) {
            background: #f8fafc;
            border-color: #94a3b8;
        }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)


def _init_state() -> None:
    defaults = {
        "case_loaded": False,
        "case_label": "",
        "loaded_source_signature": "",
        "last_upload_signature": "",
        "case": None,
        "validation_findings": [],
        "validation_ran": False,
        "validation_passed": False,
        "ybus": None,
        "ybus_built": False,
        "zbus": None,
        "zbus_method": "",
        "powerflow_done": False,
        "powerflow_result": None,
        "powerflow_method": "",
        "line_rows": [],
        "history_rows": [],
        "balance_rows": [],
        "fault_done": False,
        "fault_rows_current": [],
        "fault_rows_voltage": [],
        "fault_summary": None,
        "export_panel_open": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_after_load() -> None:
    st.session_state.validation_findings = []
    st.session_state.validation_ran = False
    st.session_state.validation_passed = False
    st.session_state.ybus = None
    st.session_state.ybus_built = False
    st.session_state.zbus = None
    st.session_state.zbus_method = ""
    st.session_state.powerflow_done = False
    st.session_state.powerflow_result = None
    st.session_state.powerflow_method = ""
    st.session_state.line_rows = []
    st.session_state.history_rows = []
    st.session_state.balance_rows = []
    st.session_state.fault_done = False
    st.session_state.fault_rows_current = []
    st.session_state.fault_rows_voltage = []
    st.session_state.fault_summary = None
    st.session_state.export_panel_open = False


def _reset_after_ybus() -> None:
    st.session_state.powerflow_done = False
    st.session_state.powerflow_result = None
    st.session_state.powerflow_method = ""
    st.session_state.line_rows = []
    st.session_state.history_rows = []
    st.session_state.balance_rows = []
    st.session_state.fault_done = False
    st.session_state.fault_rows_current = []
    st.session_state.fault_rows_voltage = []
    st.session_state.fault_summary = None


def _bus_rows(case, voltages: np.ndarray, data_form: str) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    use_polar = data_form == "polar"
    for idx, bus in enumerate(case.buses):
        v = voltages[idx]
        row: dict[str, float | int] = {
            "bus": bus.bus_i,
            "type": bus.bus_type,
            "pd_mw": float(bus.pd),
            "qd_mvar": float(bus.qd),
        }
        if use_polar:
            row["vm_pu"] = float(abs(v))
            row["va_deg"] = float(np.degrees(np.angle(v)))
        else:
            row["vr_pu"] = float(v.real)
            row["vi_pu"] = float(v.imag)
        rows.append(row)
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


def _fault_current_rows_by_form(rows: list[dict[str, float | int | str]], data_form: str) -> list[dict[str, float | str]]:
    use_polar = data_form == "polar"
    out: list[dict[str, float | str]] = []
    for row in rows:
        if use_polar:
            out.append(
                {
                    "quantity": str(row["quantity"]),
                    "mag_pu": float(row["mag_pu"]),
                    "ang_deg": float(row["ang_deg"]),
                }
            )
        else:
            out.append(
                {
                    "quantity": str(row["quantity"]),
                    "real_pu": float(row["real_pu"]),
                    "imag_pu": float(row["imag_pu"]),
                }
            )
    return out


def _fault_voltage_rows_by_form(rows: list[dict[str, float | int]], data_form: str) -> list[dict[str, float | int]]:
    use_polar = data_form == "polar"
    out: list[dict[str, float | int]] = []
    for row in rows:
        va_mag = float(row["va_mag_pu"])
        va_ang = float(row["va_ang_deg"])
        vb_mag = float(row["vb_mag_pu"])
        vb_ang = float(row["vb_ang_deg"])
        vc_mag = float(row["vc_mag_pu"])
        vc_ang = float(row["vc_ang_deg"])

        if use_polar:
            out.append(
                {
                    "bus": int(row["bus"]),
                    "va_mag_pu": va_mag,
                    "va_ang_deg": va_ang,
                    "vb_mag_pu": vb_mag,
                    "vb_ang_deg": vb_ang,
                    "vc_mag_pu": vc_mag,
                    "vc_ang_deg": vc_ang,
                }
            )
        else:
            va_complex = va_mag * np.exp(1j * np.radians(va_ang))
            vb_complex = vb_mag * np.exp(1j * np.radians(vb_ang))
            vc_complex = vc_mag * np.exp(1j * np.radians(vc_ang))
            out.append(
                {
                    "bus": int(row["bus"]),
                    "va_real_pu": float(va_complex.real),
                    "va_imag_pu": float(va_complex.imag),
                    "vb_real_pu": float(vb_complex.real),
                    "vb_imag_pu": float(vb_complex.imag),
                    "vc_real_pu": float(vc_complex.real),
                    "vc_imag_pu": float(vc_complex.imag),
                }
            )
    return out


def _to_csv_bytes(rows: list[dict[str, float | int | str]]) -> bytes:
    if not rows:
        return b""

    with io.StringIO() as sio:
        writer = csv.DictWriter(sio, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return sio.getvalue().encode("utf-8")


def _sequence_map_from_json(text: str, field_name: str) -> dict[int, float]:
    stripped = text.strip()
    if stripped == "":
        return {}

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{field_name} must be a JSON object mapping bus->value")

    out: dict[int, float] = {}
    for key, value in payload.items():
        out[int(key)] = float(value)
    return out


def _ybus_rows(case, ybus: np.ndarray, data_form: str) -> list[dict[str, float | int]]:
    use_polar = data_form == "polar"
    bus_ids = [bus.bus_i for bus in case.buses]
    rows: list[dict[str, float | int]] = []
    for i, bi in enumerate(bus_ids):
        for j, bj in enumerate(bus_ids):
            val = ybus[i, j]
            row: dict[str, float | int] = {
                "from_bus": int(bi),
                "to_bus": int(bj),
            }
            if use_polar:
                row["mag"] = float(abs(val))
                row["ang_deg"] = float(np.degrees(np.angle(val)))
            else:
                row["real"] = float(val.real)
                row["imag"] = float(val.imag)
            rows.append(row)
    return rows


def _format_complex_cell(value: complex, data_form: str) -> str:
    if data_form == "polar":
        return f"{abs(value):.6f} < {np.degrees(np.angle(value)):.2f} deg"

    imag_sign = "+" if value.imag >= 0 else "-"
    return f"{value.real:.6f} {imag_sign} j{abs(value.imag):.6f}"


def _matrix_display_rows(case, matrix: np.ndarray, data_form: str) -> list[dict[str, int | str]]:
    bus_ids = [int(bus.bus_i) for bus in case.buses]
    rows: list[dict[str, int | str]] = []

    for i, row_bus in enumerate(bus_ids):
        row: dict[str, int | str] = {"bus": row_bus}
        for j, col_bus in enumerate(bus_ids):
            row[f"bus_{col_bus}"] = _format_complex_cell(complex(matrix[i, j]), data_form)
        rows.append(row)

    return rows


def _validation_rows(findings) -> list[dict[str, str]]:
    return [
        {
            "severity": finding.severity,
            "code": finding.code,
            "message": finding.message,
        }
        for finding in findings
    ]


def _exportables_available() -> bool:
    return any(
        [
            st.session_state.validation_ran,
            st.session_state.ybus_built,
            st.session_state.powerflow_done,
            st.session_state.fault_done,
        ]
    )


def _checkbox_key(label: str) -> str:
    token = "".join(ch.lower() if ch.isalnum() else "_" for ch in label)
    return f"export_select_{token}"


def _sanitize_export_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", label.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned if cleaned else "gridsolver"


def _write_selected_exports(
    selected_exports: dict[str, tuple[str, bytes, str]],
    export_label: str,
) -> Path:
    root = Path(__file__).resolve().parents[2] / "exports"
    root.mkdir(parents=True, exist_ok=True)

    label = _sanitize_export_label(export_label)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = root / f"{label}_{timestamp}"
    target_dir.mkdir(parents=False, exist_ok=False)

    for filename, data_bytes, _mime in selected_exports.values():
        (target_dir / filename).write_bytes(data_bytes)

    return target_dir


def main() -> None:
    st.set_page_config(page_title="GridSolver", layout="wide")
    _init_state()

    top1, top2, top3 = st.columns([4, 1, 1])
    with top1:
        st.markdown("##### GridSolver")
        st.caption("Workflow: Load File -> Validate -> Build Ybus -> Power Flow -> Fault Study -> Export")
    with top2:
        dark_mode = st.toggle("Dark Theme", value=True)
    with top3:
        data_form_label = st.radio("Data Form", ["Polar", "Rectangular"], horizontal=False)
    data_form = "polar" if data_form_label == "Polar" else "rectangular"

    _apply_theme_css(dark_mode)

    options = _default_case_options()
    fault_type_map = _fault_type_options()

    st.sidebar.header("System Input")
    selected_case_name = st.sidebar.selectbox("Bundled case", list(options.keys()))
    uploaded_file = st.sidebar.file_uploader(
        "Upload MATPOWER-style .m file",
        type=["m", "txt"],
        key="system_case_upload",
    )

    st.sidebar.header("Power Flow Settings")
    method = st.sidebar.selectbox("Solver", ["GS", "NR"])
    tolerance = st.sidebar.number_input("Tolerance", min_value=1e-10, max_value=1.0, value=1e-6, format="%.1e")
    max_iterations = st.sidebar.number_input("Max iterations", min_value=1, max_value=5000, value=200, step=1)

    st.sidebar.header("Fault Study Panel")
    fault_type_label = st.sidebar.selectbox("Fault type", list(fault_type_map.keys()))
    fault_type = fault_type_map[fault_type_label]
    fault_target = st.sidebar.radio("Faulted element", ["Bus", "Line"], horizontal=True)

    fault_bus = None
    fault_line_idx = None
    if st.session_state.case_loaded and st.session_state.case is not None:
        case = st.session_state.case
        bus_ids = [bus.bus_i for bus in case.buses]
        if fault_target == "Bus":
            fault_bus = st.sidebar.selectbox("Faulted bus", bus_ids)
        else:
            labels = [
                f"Line {idx + 1}: {br.fbus}->{br.tbus} (r={br.r:.4f}, x={br.x:.4f})"
                for idx, br in enumerate(case.branches)
            ]
            if labels:
                selected_label = st.sidebar.selectbox("Faulted line", labels)
                fault_line_idx = labels.index(selected_label)
                st.sidebar.info(
                    "Current solver is bus-based; line selection is mapped to the line from-bus equivalent."
                )
            else:
                st.sidebar.warning("No branches available for line fault selection.")
    else:
        st.sidebar.caption("Load system file first to choose fault location.")

    zf_r = st.sidebar.number_input("Fault impedance Rf (p.u.)", value=0.0, step=0.01, format="%.4f")
    zf_x = st.sidebar.number_input("Fault impedance Xf (p.u.)", value=0.0, step=0.01, format="%.4f")

    with st.sidebar.expander("Sequence Data (Advanced / optional)"):
        default_xdpp = st.number_input("Default X''d (p.u.)", min_value=0.01, max_value=10.0, value=0.2, step=0.01)
        x1_text = st.text_area("X1 overrides by bus (JSON)", value="{}", height=80)
        x2_text = st.text_area("X2 overrides by bus (JSON)", value="{}", height=80)
        x0_text = st.text_area("X0 overrides by bus (JSON)", value="{}", height=80)

    selected_source_signature = _selected_source_signature(selected_case_name, uploaded_file)
    auto_load_from_upload = False
    if uploaded_file is not None:
        if selected_source_signature != st.session_state.last_upload_signature:
            st.session_state.last_upload_signature = selected_source_signature
            auto_load_from_upload = True
    else:
        st.session_state.last_upload_signature = ""

    if (
        st.session_state.case_loaded
        and st.session_state.loaded_source_signature != ""
        and selected_source_signature != st.session_state.loaded_source_signature
    ):
        st.session_state.case = None
        st.session_state.case_loaded = False
        st.session_state.case_label = ""
        st.session_state.loaded_source_signature = ""
        _reset_after_load()
        st.info("System input changed. Workflow reset. Load the selected file/case to continue.")

    st.subheader("Operation Steps")
    c1, c2, c3, c4, c5, c6 = st.columns(6, gap="small")
    click_load = c1.button("Load File", use_container_width=True, type="primary")
    click_validate = c2.button(
        "Validate",
        use_container_width=True,
        type="primary",
        disabled=not st.session_state.case_loaded,
    )
    click_ybus = c3.button(
        "Create Ybus",
        use_container_width=True,
        type="primary",
        disabled=not (st.session_state.validation_ran and st.session_state.validation_passed),
    )
    click_pf = c4.button(
        "Power Flow",
        use_container_width=True,
        type="primary",
        disabled=not st.session_state.ybus_built,
    )
    click_fault = c5.button(
        "Fault Study",
        use_container_width=True,
        type="primary",
        disabled=not (
            st.session_state.powerflow_done
            and st.session_state.powerflow_result is not None
            and st.session_state.powerflow_result.converged
        ),
    )
    click_export = c6.button(
        "Export",
        use_container_width=True,
        type="primary",
        disabled=not _exportables_available(),
    )

    needs_refresh = False

    if click_load or auto_load_from_upload:
        try:
            loaded_case, loaded_label, loaded_signature = _load_case_from_selection(
                options, selected_case_name, uploaded_file
            )
            st.session_state.case = loaded_case
            st.session_state.case_loaded = True
            st.session_state.case_label = loaded_label
            st.session_state.loaded_source_signature = loaded_signature
            _reset_after_load()
            if auto_load_from_upload and not click_load:
                st.success(f"Loaded case from upload: {st.session_state.case_label}")
            else:
                st.success(f"Loaded case: {st.session_state.case_label}")
            needs_refresh = True
        except Exception as exc:  # pylint: disable=broad-except
            st.session_state.case = None
            st.session_state.case_loaded = False
            st.session_state.case_label = ""
            st.session_state.loaded_source_signature = ""
            _reset_after_load()
            st.error(f"Load failed: {exc}")

    if click_validate:
        case = st.session_state.case
        if case is None:
            st.error("Load a case first.")
        else:
            findings = validate_case_data(case)
            st.session_state.validation_findings = findings
            st.session_state.validation_ran = True
            st.session_state.validation_passed = not has_validation_errors(findings)
            if st.session_state.validation_passed:
                st.success("Validation passed with no blocking errors.")
                needs_refresh = True
            else:
                st.error("Validation found blocking errors. Review findings before proceeding.")

    if click_ybus:
        case = st.session_state.case
        if case is None:
            st.error("Load a case first.")
        else:
            try:
                ybus = build_ybus(case)
                zbus_method = "Inverse"
                try:
                    zbus = np.linalg.inv(ybus)
                except np.linalg.LinAlgError:
                    zbus = np.linalg.pinv(ybus)
                    zbus_method = "Pseudo-inverse (Ybus is singular)"

                st.session_state.ybus = ybus
                st.session_state.ybus_built = True
                st.session_state.zbus = zbus
                st.session_state.zbus_method = zbus_method
                _reset_after_ybus()
                st.success(f"Ybus built successfully ({ybus.shape[0]}x{ybus.shape[1]}).")
                if zbus_method != "Inverse":
                    st.warning("Zbus computed with pseudo-inverse because Ybus is singular.")
                needs_refresh = True
            except Exception as exc:  # pylint: disable=broad-except
                st.session_state.ybus = None
                st.session_state.ybus_built = False
                st.session_state.zbus = None
                st.session_state.zbus_method = ""
                _reset_after_ybus()
                st.error(f"Ybus build failed: {exc}")

    if click_pf:
        case = st.session_state.case
        if case is None or not st.session_state.ybus_built:
            st.error("Load case and build Ybus before running power flow.")
        else:
            try:
                if method == "GS":
                    result = solve_gauss_seidel(case, tolerance=float(tolerance), max_iterations=int(max_iterations))
                else:
                    result = solve_newton_raphson(case, tolerance=float(tolerance), max_iterations=int(max_iterations))

                flows = compute_line_flows(case, result.voltages)
                balance = compute_power_balance(case, result.voltages, flows)

                st.session_state.powerflow_done = True
                st.session_state.powerflow_result = result
                st.session_state.powerflow_method = method
                st.session_state.line_rows = _line_rows(flows)
                st.session_state.history_rows = _history_rows(method, result.history)
                st.session_state.balance_rows = [balance]

                st.session_state.fault_done = False
                st.session_state.fault_rows_current = []
                st.session_state.fault_rows_voltage = []
                st.session_state.fault_summary = None

                if result.converged:
                    st.success(f"Power flow converged in {result.iterations} iterations ({method}).")
                    needs_refresh = True
                else:
                    st.warning("Power flow did not converge at current settings.")
            except Exception as exc:  # pylint: disable=broad-except
                st.session_state.powerflow_done = False
                st.session_state.powerflow_result = None
                st.error(f"Power flow failed: {exc}")

    if click_fault:
        case = st.session_state.case
        result = st.session_state.powerflow_result

        if case is None or result is None or not result.converged:
            st.error("Run a converged power flow before fault study.")
        else:
            try:
                seq_x1 = _sequence_map_from_json(x1_text, "X1 overrides")
                seq_x2 = _sequence_map_from_json(x2_text, "X2 overrides")
                seq_x0 = _sequence_map_from_json(x0_text, "X0 overrides")

                selected_fault_bus = fault_bus
                fault_note = ""
                if fault_target == "Line":
                    if fault_line_idx is None or fault_line_idx >= len(case.branches):
                        raise ValueError("Select a valid faulted line.")
                    branch = case.branches[fault_line_idx]
                    selected_fault_bus = branch.fbus
                    fault_note = f"Line-selected fault mapped to from-bus {branch.fbus}."

                if selected_fault_bus is None:
                    raise ValueError("Select faulted bus/line before running fault study.")

                fault_result = analyze_fault(
                    case=case,
                    pre_fault_voltages=result.voltages,
                    fault_bus=int(selected_fault_bus),
                    fault_type=fault_type,
                    fault_impedance_pu=complex(float(zf_r), float(zf_x)),
                    default_gen_xdpp_pu=float(default_xdpp),
                    gen_x1_pu_by_bus=seq_x1,
                    gen_x2_pu_by_bus=seq_x2,
                    gen_x0_pu_by_bus=seq_x0,
                )

                st.session_state.fault_done = True
                st.session_state.fault_rows_current = fault_current_rows(fault_result)
                st.session_state.fault_rows_voltage = post_fault_voltage_rows(case, fault_result)
                st.session_state.fault_summary = {
                    "fault_type": fault_type_label,
                    "solver_fault_code": fault_result.fault_type,
                    "fault_target": fault_target,
                    "fault_bus_used": int(selected_fault_bus),
                    "fault_impedance": complex(float(zf_r), float(zf_x)),
                    "ia_mag": float(abs(fault_result.ia_pu)),
                    "note": fault_note,
                }
                st.success("Fault study completed.")
            except Exception as exc:  # pylint: disable=broad-except
                st.session_state.fault_done = False
                st.session_state.fault_rows_current = []
                st.session_state.fault_rows_voltage = []
                st.session_state.fault_summary = None
                st.error(f"Fault study failed: {exc}")

    if click_export:
        st.session_state.export_panel_open = True

    if needs_refresh:
        st.rerun()

    st.markdown("### Workflow Status")
    st.markdown(
        " | ".join(
            [
                f"`Load: {'Done' if st.session_state.case_loaded else 'Pending'}`",
                f"`Validate: {'Done' if st.session_state.validation_ran else 'Pending'}`",
                f"`Ybus: {'Done' if st.session_state.ybus_built else 'Pending'}`",
                f"`Power Flow: {'Done' if st.session_state.powerflow_done else 'Pending'}`",
                f"`Fault: {'Done' if st.session_state.fault_done else 'Pending'}`",
            ]
        )
    )

    if st.session_state.case_loaded:
        st.info(f"Loaded case: {st.session_state.case_label}")

    if st.session_state.validation_ran:
        st.subheader("Validation Results")
        finding_rows = _validation_rows(st.session_state.validation_findings)
        if finding_rows:
            st.dataframe(finding_rows, use_container_width=True)
        else:
            st.success("No validation findings.")

    if st.session_state.ybus_built and st.session_state.ybus is not None and st.session_state.case is not None:
        st.subheader("Ybus and Zbus Matrices")
        ybus = st.session_state.ybus
        st.write(f"Size: `{ybus.shape[0]} x {ybus.shape[1]}`")
        st.caption(f"Display format: {data_form_label}")

        tab_ybus, tab_zbus = st.tabs(["Ybus", "Zbus"])
        with tab_ybus:
            st.dataframe(
                _matrix_display_rows(st.session_state.case, ybus, data_form),
                use_container_width=True,
            )
        with tab_zbus:
            zbus = st.session_state.zbus
            if zbus is None:
                st.warning("Zbus is not available for the current case.")
            else:
                st.write(f"Computed from Ybus using: `{st.session_state.zbus_method}`")
                st.dataframe(
                    _matrix_display_rows(st.session_state.case, zbus, data_form),
                    use_container_width=True,
                )

    if st.session_state.powerflow_done and st.session_state.powerflow_result is not None and st.session_state.case is not None:
        result = st.session_state.powerflow_result
        case = st.session_state.case
        bus_rows = _bus_rows(case, result.voltages, data_form)

        st.subheader("Power Flow Results")
        p1, p2, p3 = st.columns(3)
        p1.metric("Solver", st.session_state.powerflow_method)
        p2.metric("Converged", str(result.converged))
        p3.metric("Iterations", str(result.iterations))

        st.markdown(f"**Bus Voltages ({data_form_label})**")
        st.dataframe(bus_rows, use_container_width=True)

        st.markdown("**Line Flows and Losses**")
        st.dataframe(st.session_state.line_rows, use_container_width=True)

        st.markdown("**Power Balance**")
        st.dataframe(st.session_state.balance_rows, use_container_width=True)

        st.markdown("**Iteration History**")
        st.dataframe(st.session_state.history_rows, use_container_width=True)

    if st.session_state.fault_done and st.session_state.fault_summary is not None:
        summary = st.session_state.fault_summary
        current_rows = _fault_current_rows_by_form(st.session_state.fault_rows_current, data_form)
        voltage_rows = _fault_voltage_rows_by_form(st.session_state.fault_rows_voltage, data_form)

        st.subheader("Fault Study Results")
        f1, f2, f3 = st.columns(3)
        f1.metric("Fault Type", summary["fault_type"])
        f2.metric("Fault Bus Used", f"Bus {summary['fault_bus_used']}")
        f3.metric("|Ia| (p.u.)", f"{summary['ia_mag']:.6f}")

        zf = summary["fault_impedance"]
        st.write(f"Fault impedance Zf (p.u.): `{zf.real:.4f} + j{zf.imag:.4f}`")
        if summary["note"]:
            st.warning(summary["note"])

        st.markdown(f"**Fault Currents ({data_form_label})**")
        st.dataframe(current_rows, use_container_width=True)

        st.markdown(f"**Post-Fault Bus Voltages ({data_form_label})**")
        st.dataframe(voltage_rows, use_container_width=True)

    if st.session_state.export_panel_open or _exportables_available():
        st.subheader("Export Results")

        available: dict[str, tuple[str, bytes, str]] = {}

        if st.session_state.validation_ran:
            available["Validation Findings"] = (
                "validation_findings.csv",
                _to_csv_bytes(_validation_rows(st.session_state.validation_findings)),
                "text/csv",
            )

        if st.session_state.ybus_built and st.session_state.ybus is not None and st.session_state.case is not None:
            available["Ybus Matrix"] = (
                "ybus_matrix.csv",
                _to_csv_bytes(_ybus_rows(st.session_state.case, st.session_state.ybus, data_form)),
                "text/csv",
            )
            if st.session_state.zbus is not None:
                available["Zbus Matrix"] = (
                    "zbus_matrix.csv",
                    _to_csv_bytes(_ybus_rows(st.session_state.case, st.session_state.zbus, data_form)),
                    "text/csv",
                )

        if st.session_state.powerflow_done and st.session_state.powerflow_result is not None and st.session_state.case is not None:
            case = st.session_state.case
            result = st.session_state.powerflow_result
            available["Bus Results"] = (
                "bus_results.csv",
                _to_csv_bytes(_bus_rows(case, result.voltages, data_form)),
                "text/csv",
            )
            available["Line Flows"] = (
                "line_flows.csv",
                _to_csv_bytes(st.session_state.line_rows),
                "text/csv",
            )
            available["Iteration History"] = (
                "iteration_history.csv",
                _to_csv_bytes(st.session_state.history_rows),
                "text/csv",
            )
            available["Power Balance"] = (
                "power_balance.csv",
                _to_csv_bytes(st.session_state.balance_rows),
                "text/csv",
            )

        if st.session_state.fault_done and st.session_state.fault_summary is not None:
            available["Fault Currents"] = (
                "fault_currents.csv",
                _to_csv_bytes(_fault_current_rows_by_form(st.session_state.fault_rows_current, data_form)),
                "text/csv",
            )
            available["Post-Fault Voltages"] = (
                "post_fault_voltages.csv",
                _to_csv_bytes(_fault_voltage_rows_by_form(st.session_state.fault_rows_voltage, data_form)),
                "text/csv",
            )

        summary_lines: list[str] = []
        if st.session_state.case_loaded:
            summary_lines.append(f"Case: {st.session_state.case_label}")
        summary_lines.append(f"Data form: {data_form_label}")
        if st.session_state.powerflow_done and st.session_state.powerflow_result is not None:
            pf = st.session_state.powerflow_result
            summary_lines.append(f"Power flow solver: {st.session_state.powerflow_method}")
            summary_lines.append(f"Converged: {pf.converged}")
            summary_lines.append(f"Iterations: {pf.iterations}")
        if st.session_state.fault_done and st.session_state.fault_summary is not None:
            fs = st.session_state.fault_summary
            summary_lines.append(f"Fault type: {fs['fault_type']}")
            summary_lines.append(f"Fault bus used: {fs['fault_bus_used']}")
            summary_lines.append(f"|Ia| (p.u.): {fs['ia_mag']:.6e}")

        if summary_lines:
            available["Summary Text"] = (
                "summary.txt",
                ("\n".join(summary_lines) + "\n").encode("utf-8"),
                "text/plain",
            )

        if not available:
            st.info("No exportable results yet.")
        else:
            st.markdown("Select datasets to export:")

            default_label = st.session_state.case_label if st.session_state.case_label else "gridsolver"
            export_label = st.text_input(
                "Export folder label",
                value=default_label,
                help="A timestamp will be appended automatically.",
            )

            left_col, right_col = st.columns(2, gap="large")
            labels = list(available.keys())
            for idx, label in enumerate(labels):
                key = _checkbox_key(label)
                if key not in st.session_state:
                    st.session_state[key] = True
                if idx % 2 == 0:
                    left_col.checkbox(label, key=key)
                else:
                    right_col.checkbox(label, key=key)

            selected_exports = {
                label: payload
                for label, payload in available.items()
                if st.session_state.get(_checkbox_key(label), False)
            }

            if selected_exports:
                st.caption("Export destination: `exports/<label>_<YYYYMMDD_HHMMSS>/`")
            else:
                st.warning("Select at least one dataset to export.")

            if st.button("Export", type="primary", disabled=not selected_exports):
                try:
                    target_dir = _write_selected_exports(selected_exports, export_label)
                    st.success(
                        f"Exported {len(selected_exports)} file(s) to `{target_dir}`"
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    st.error(f"Export failed: {exc}")


if __name__ == "__main__":
    main()
