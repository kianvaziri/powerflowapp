"""Workflow-driven Streamlit UI for power flow and fault studies."""

from __future__ import annotations

import csv
import html
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
from src.shortcircuit import analyze_fault, fault_current_rows, fault_diagnostic_rows, post_fault_voltage_rows
from src.validation import has_validation_errors, validate_case_data
from src.ybus import build_ybus


def _default_case_options() -> dict[str, Path]:
    root = Path(__file__).resolve().parents[2]
    return {
        "IEEE 14-bus": root / "data" / "raw" / "ieee14" / "case14_sample.m",
        "IEEE 14-bus literature sequence": root / "data" / "raw" / "ieee14" / "case14_literature_sequence.m",
        "IEEE 14-bus PowerWorld branch sequence": root / "data" / "raw" / "ieee14" / "case14_powerworld_branch_sequence.m",
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


def _apply_theme_css() -> None:
    css = """
    <style>
    :root {
        --gs-bg: var(--st-background-color, var(--background-color, #ffffff));
        --gs-surface: var(--st-secondary-background-color, var(--secondary-background-color, #f0f2f6));
        --gs-border: var(--st-border-color, rgba(128, 128, 128, 0.35));
        --gs-text: var(--st-text-color, var(--text-color, #262730));
        --gs-primary: var(--st-primary-color, var(--primary-color, #2563eb));
        --gs-primary-soft: color-mix(in srgb, var(--gs-surface) 82%, var(--gs-primary) 18%);
        --gs-primary-hover: color-mix(in srgb, var(--gs-surface) 70%, var(--gs-primary) 30%);
        --gs-disabled: var(--st-border-color-light, rgba(128, 128, 128, 0.5));
    }

    .stApp {
        font-size: 1.04rem;
        color: var(--gs-text);
        background-color: var(--gs-bg);
    }

    [data-testid="stSidebar"] { font-size: 1.02rem; }

    [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"] p,
    label,
    .stRadio label,
    .stCheckbox label,
    .stSelectbox label,
    .stTextInput label,
    .stNumberInput label,
    .stFileUploader label {
        font-size: 1.05rem;
        color: var(--gs-text) !important;
    }

    [data-testid="stMetricValue"] { color: var(--gs-text) !important; font-size: 1.55rem; }
    [data-testid="stMetricLabel"] p { font-size: 1.03rem; color: var(--gs-text) !important; }
    div[data-testid="stDataFrame"] { font-size: 1.04rem; }
    [data-testid="stTable"] table { font-size: 1.1rem; }
    [data-testid="stTable"] th,
    [data-testid="stTable"] td { padding: 0.45rem 0.6rem; }

    .workflow-step {
        padding: 0.25rem 0.4rem;
        border-radius: 0.4rem;
        background: color-mix(in srgb, var(--gs-surface) 92%, transparent);
    }

    div.stButton > button {
        width: 100%;
        min-height: 3.15rem;
        border-radius: 0.75rem;
        border: 1px solid var(--gs-border) !important;
        background: var(--gs-surface) !important;
        color: var(--gs-text) !important;
        -webkit-text-fill-color: var(--gs-text) !important;
        -webkit-appearance: none;
        appearance: none;
        font-family: Calibri, "Segoe UI", sans-serif;
        font-size: 1.06rem;
        font-weight: 650;
        letter-spacing: 0.01em;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
        transition: all 0.18s ease;
    }

    div.stButton > button * {
        color: inherit !important;
        -webkit-text-fill-color: inherit !important;
    }

    div.stButton > button:hover:not(:disabled) {
        border-color: var(--gs-primary) !important;
        background: color-mix(in srgb, var(--gs-surface) 80%, var(--gs-primary) 20%) !important;
        color: var(--gs-text) !important;
        -webkit-text-fill-color: var(--gs-text) !important;
    }

    div.stButton > button:active:not(:disabled) {
        transform: translateY(1px);
    }

    div.stButton > button:focus {
        outline: none;
        box-shadow: 0 0 0 0.2rem color-mix(in srgb, var(--gs-primary) 35%, transparent);
    }

    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="baseButton-primary"],
    div.stButton > button[data-testid="stBaseButton-primary"] {
        background: var(--gs-primary-soft) !important;
        color: var(--gs-text) !important;
        -webkit-text-fill-color: var(--gs-text) !important;
        border-color: var(--gs-primary) !important;
    }

    div.stButton > button[kind="primary"] *,
    div.stButton > button[data-testid="baseButton-primary"] *,
    div.stButton > button[data-testid="stBaseButton-primary"] * {
        color: var(--gs-text) !important;
        -webkit-text-fill-color: var(--gs-text) !important;
    }

    div.stButton > button[kind="primary"]:hover:not(:disabled),
    div.stButton > button[data-testid="baseButton-primary"]:hover:not(:disabled),
    div.stButton > button[data-testid="stBaseButton-primary"]:hover:not(:disabled),
    div.stButton > button[kind="primary"]:focus:not(:disabled),
    div.stButton > button[data-testid="baseButton-primary"]:focus:not(:disabled),
    div.stButton > button[data-testid="stBaseButton-primary"]:focus:not(:disabled),
    div.stButton > button[kind="primary"]:active:not(:disabled),
    div.stButton > button[data-testid="baseButton-primary"]:active:not(:disabled),
    div.stButton > button[data-testid="stBaseButton-primary"]:active:not(:disabled) {
        background: var(--gs-primary-hover) !important;
        border-color: var(--gs-primary-hover) !important;
        color: var(--gs-text) !important;
        -webkit-text-fill-color: var(--gs-text) !important;
    }

    div.stButton > button:disabled {
        opacity: 1;
        color: var(--gs-disabled) !important;
        -webkit-text-fill-color: var(--gs-disabled) !important;
        border-color: var(--gs-border) !important;
        cursor: not-allowed;
        box-shadow: none;
    }

    div.stButton > button:disabled * {
        color: var(--gs-disabled) !important;
        -webkit-text-fill-color: var(--gs-disabled) !important;
    }

    div.stDownloadButton > button {
        border-radius: 0.65rem;
        min-height: 2.65rem;
        font-family: Calibri, "Segoe UI", sans-serif;
        font-size: 1.03rem;
        color: var(--gs-text) !important;
        -webkit-text-fill-color: var(--gs-text) !important;
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
        "fault_rows_diagnostic": [],
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
    st.session_state.fault_rows_diagnostic = []
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
    st.session_state.fault_rows_diagnostic = []
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


def _parse_branch_key(raw_key: str, field_name: str) -> tuple[int, int]:
    token = raw_key.strip()
    if "-" in token:
        left, right = token.split("-", 1)
    elif ":" in token:
        left, right = token.split(":", 1)
    elif "," in token:
        left, right = token.split(",", 1)
    else:
        raise ValueError(f"{field_name} key '{raw_key}' must use 'from-to' format")

    fbus = int(left.strip())
    tbus = int(right.strip())
    if fbus <= tbus:
        return fbus, tbus
    return tbus, fbus


def _branch_scale_map_from_json(text: str, field_name: str) -> dict[tuple[int, int], float]:
    stripped = text.strip()
    if stripped == "":
        return {}

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{field_name} must be a JSON object mapping 'from-to' -> scale")

    out: dict[tuple[int, int], float] = {}
    for key, value in payload.items():
        parsed = _parse_branch_key(str(key), field_name)
        out[parsed] = float(value)
    return out


def _branch_block_set_from_text(text: str, field_name: str) -> set[tuple[int, int]]:
    stripped = text.strip()
    if stripped == "":
        return set()

    chunks = [part.strip() for part in stripped.split(",") if part.strip()]
    out: set[tuple[int, int]] = set()
    for chunk in chunks:
        out.add(_parse_branch_key(chunk, field_name))
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


DATAFRAME_ROW_HEIGHT = 34


def _show_dataframe(data) -> None:
    st.dataframe(data, use_container_width=True, row_height=DATAFRAME_ROW_HEIGHT)


def _show_large_table(data) -> None:
    st.table(data)


def _theme_plot_colors() -> dict[str, str]:
    theme_base = st.get_option("theme.base") or "light"
    if theme_base == "dark":
        return {
            "text": "#e5e7eb",
            "line": "#94a3b8",
            "bus": "#60a5fa",
            "pq": "#60a5fa",
            "pv": "#34d399",
            "slack": "#f59e0b",
            "background": "#0f172a",
            "tooltip_bg": "#111827",
            "tooltip_border": "#475569",
            "tooltip_text": "#f8fafc",
        }
    return {
        "text": "#1f2937",
        "line": "#64748b",
        "bus": "#2563eb",
        "pq": "#2563eb",
        "pv": "#059669",
        "slack": "#d97706",
        "background": "#ffffff",
        "tooltip_bg": "#ffffff",
        "tooltip_border": "#cbd5e1",
        "tooltip_text": "#111827",
    }


def _topology_positions(case) -> dict[int, tuple[float, float]]:
    bus_ids = [bus.bus_i for bus in case.buses]
    total = len(bus_ids)
    if total == 0:
        return {}

    positions: dict[int, tuple[float, float]] = {}
    start_angle = np.pi / 2.0
    for idx, bus_id in enumerate(bus_ids):
        angle = start_angle - (2.0 * np.pi * idx / total)
        positions[bus_id] = (float(np.cos(angle)), float(np.sin(angle)))
    return positions


def _plot_case_topology(case) -> None:
    positions = _topology_positions(case)
    if not positions:
        st.info("No buses available to draw.")
        return

    colors = _theme_plot_colors()
    canvas_size = 647
    center = canvas_size / 2.0
    layout_radius = canvas_size * 0.37
    node_radius = 18
    slack_radius = 20
    font_size = 11.25
    tooltip_width = 230
    tooltip_height = 46

    def to_canvas(point: tuple[float, float]) -> tuple[float, float]:
        x, y = point
        return center + (x * layout_radius), center - (y * layout_radius)

    def tooltip_origin(x: float, y: float) -> tuple[float, float]:
        tooltip_x = min(max(x + 16, 8), canvas_size - tooltip_width - 8)
        tooltip_y = min(max(y - tooltip_height - 16, 8), canvas_size - tooltip_height - 8)
        return tooltip_x, tooltip_y

    def tooltip_svg(x: float, y: float, line_1: str, line_2: str) -> str:
        tx, ty = tooltip_origin(x, y)
        first = html.escape(line_1)
        second = html.escape(line_2)
        return (
            f"<g class='topology-tooltip' transform='translate({tx:.1f} {ty:.1f})'>"
            f"<rect width='{tooltip_width}' height='{tooltip_height}' rx='6' fill='{colors['tooltip_bg']}' "
            f"stroke='{colors['tooltip_border']}' stroke-width='1' opacity='0.98' />"
            f"<text x='10' y='18' font-family='Calibri, Arial, sans-serif' font-size='12' "
            f"font-weight='700' fill='{colors['tooltip_text']}'>{first}</text>"
            f"<text x='10' y='36' font-family='Calibri, Arial, sans-serif' font-size='11' "
            f"fill='{colors['tooltip_text']}'>{second}</text></g>"
        )

    def bus_color(bus_type: int) -> str:
        if bus_type == 3:
            return colors["slack"]
        if bus_type == 2:
            return colors["pv"]
        return colors["pq"]

    branch_elements: list[str] = []
    for branch in case.branches:
        if branch.status == 0:
            continue
        start = positions.get(branch.fbus)
        end = positions.get(branch.tbus)
        if start is None or end is None:
            continue
        x1, y1 = to_canvas(start)
        x2, y2 = to_canvas(end)
        mid_x = (x1 + x2) / 2.0
        mid_y = (y1 + y2) / 2.0
        branch_elements.append(
            f"<g class='topology-item'>"
            f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' "
            f"stroke='{colors['line']}' stroke-width='2' stroke-linecap='round' opacity='0.88' />"
            f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' "
            f"stroke='transparent' stroke-width='18' stroke-linecap='round' />"
            f"{tooltip_svg(mid_x, mid_y, f'Branch {branch.fbus} -> {branch.tbus}', f'r={branch.r:.5f}, x={branch.x:.5f}, b={branch.b:.5f}')}"
            f"</g>"
        )

    bus_elements: list[str] = []
    for bus in case.buses:
        x, y = to_canvas(positions[bus.bus_i])
        is_slack = bus.bus_type == 3
        radius = slack_radius if is_slack else node_radius
        fill = bus_color(bus.bus_type)
        bus_type = {1: "PQ", 2: "PV", 3: "Slack"}.get(bus.bus_type, str(bus.bus_type))
        bus_elements.append(
            f"<g class='topology-item' style='cursor:default;'>"
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{radius}' fill='{fill}' stroke='{colors['background']}' stroke-width='2' />"
            f"<text x='{x:.1f}' y='{y + 2:.1f}' text-anchor='middle' font-family='Calibri, Arial, sans-serif' "
            f"font-size='{font_size}' font-weight='600' fill='#ffffff'>{bus.bus_i}</text>"
            f"{tooltip_svg(x, y, f'Bus {bus.bus_i} ({bus_type})', f'Pd={bus.pd:.3f} MW, Qd={bus.qd:.3f} MVAr')}"
            f"</g>"
        )

    legend_items = [
        ("PQ", colors["pq"]),
        ("PV", colors["pv"]),
        ("Slack", colors["slack"]),
    ]
    legend = "".join(
        f"<span style='display:inline-flex; align-items:center; gap:0.35rem; margin:0 0.55rem;'>"
        f"<span style='width:0.7rem; height:0.7rem; border-radius:50%; background:{color}; "
        f"display:inline-block;'></span>{html.escape(label)}</span>"
        for label, color in legend_items
    )

    svg = f"""
    <div style='display:flex; justify-content:center; width:100%; margin:0.25rem 0 0.5rem 0;'>
      <div>
        <style>
          .topology-tooltip {{ opacity: 0; pointer-events: none; transition: opacity 120ms ease; }}
          .topology-item:hover .topology-tooltip {{ opacity: 1; }}
          .topology-item:hover circle {{ filter: brightness(1.08); }}
          .topology-item:hover line:first-child {{ stroke-width: 3; }}
        </style>
        <svg width='{canvas_size}' height='{canvas_size}' viewBox='0 0 {canvas_size} {canvas_size}' role='img'
             aria-label='Bus topology diagram'
             style='background:{colors["background"]}; border:1px solid {colors["line"]}22; border-radius:12px; max-width:100%;'>
          {''.join(branch_elements)}
          {''.join(bus_elements)}
        </svg>
        <div style='display:flex; justify-content:center; flex-wrap:wrap; font-family:Calibri, Arial, sans-serif; font-size:1.08rem; color:{colors['text']}; margin-top:0.45rem;'>
          {legend}
        </div>
      </div>
    </div>
    """
    st.components.v1.html(svg, height=canvas_size + 76)


def main() -> None:
    st.set_page_config(page_title="GridSolver", layout="wide")
    _init_state()

    top1, top2 = st.columns([4, 1])
    with top1:
        st.markdown("##### GridSolver")
        st.caption("Workflow: Load File -> Validate -> Build Ybus -> Power Flow -> Fault Study -> Export")
    with top2:
        data_form_label = st.radio("Data Form", ["Polar", "Rectangular"], horizontal=False)
    data_form = "polar" if data_form_label == "Polar" else "rectangular"

    _apply_theme_css()

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
        branch_zero_seq_scale = st.number_input(
            "Branch Z0/Z1 scale",
            min_value=0.1,
            max_value=20.0,
            value=2.5,
            step=0.1,
        )
        fault_include_bus_shunts = st.checkbox("Include bus shunts in sequence networks", value=False)
        fault_include_line_charging = st.checkbox("Include line charging in sequence networks", value=False)
        sequence_on_gen_mbase = st.checkbox(
            "Generator sequence data uses generator MVA base",
            value=True,
            help="Matches most short-circuit tools: generator R/X sequence values are converted to the system base.",
        )
        branch_scale_text = st.text_area(
            "Branch Z0/Z1 overrides (JSON: {'4-7': 3.0})",
            value="{}",
            height=80,
        )
        blocked_branch_text = st.text_input(
            "Zero-sequence blocked branches (comma list: 4-7,4-9)",
            value="",
        )
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
                st.session_state.fault_rows_diagnostic = []
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
                branch_scale_map = _branch_scale_map_from_json(branch_scale_text, "Branch Z0/Z1 overrides")
                blocked_zero_seq = _branch_block_set_from_text(
                    blocked_branch_text,
                    "Zero-sequence blocked branches",
                )

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
                    branch_zero_seq_scale=float(branch_zero_seq_scale),
                    branch_zero_seq_scale_by_branch=branch_scale_map,
                    zero_seq_blocked_branches=blocked_zero_seq,
                    include_bus_shunts=bool(fault_include_bus_shunts),
                    include_line_charging=bool(fault_include_line_charging),
                    sequence_data_on_gen_mbase=bool(sequence_on_gen_mbase),
                )

                st.session_state.fault_done = True
                st.session_state.fault_rows_current = fault_current_rows(fault_result)
                st.session_state.fault_rows_diagnostic = fault_diagnostic_rows(fault_result)
                st.session_state.fault_rows_voltage = post_fault_voltage_rows(case, fault_result)
                st.session_state.fault_summary = {
                    "fault_type": fault_type_label,
                    "solver_fault_code": fault_result.fault_type,
                    "fault_target": fault_target,
                    "fault_bus_used": int(selected_fault_bus),
                    "fault_impedance": complex(float(zf_r), float(zf_x)),
                    "ia_mag": float(abs(fault_result.ia_pu)),
                    "branch_zero_seq_scale": float(branch_zero_seq_scale),
                    "branch_scale_override_count": len(branch_scale_map),
                    "blocked_zero_seq_count": len(blocked_zero_seq),
                    "include_bus_shunts": bool(fault_include_bus_shunts),
                    "include_line_charging": bool(fault_include_line_charging),
                    "sequence_on_gen_mbase": bool(sequence_on_gen_mbase),
                    "note": fault_note,
                }
                st.success("Fault study completed.")
            except Exception as exc:  # pylint: disable=broad-except
                st.session_state.fault_done = False
                st.session_state.fault_rows_current = []
                st.session_state.fault_rows_diagnostic = []
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
        if st.session_state.case is not None:
            st.subheader("System Topology")
            st.caption("Buses are arranged on a circle; straight lines show branch connectivity.")
            _plot_case_topology(st.session_state.case)

    if st.session_state.validation_ran:
        st.subheader("Validation Results")
        finding_rows = _validation_rows(st.session_state.validation_findings)
        if finding_rows:
            _show_dataframe(finding_rows)
        else:
            st.success("No validation findings.")

    if st.session_state.ybus_built and st.session_state.ybus is not None and st.session_state.case is not None:
        st.subheader("Ybus and Zbus Matrices")
        ybus = st.session_state.ybus
        st.write(f"Size: `{ybus.shape[0]} x {ybus.shape[1]}`")
        st.caption(f"Display format: {data_form_label}")

        tab_ybus, tab_zbus = st.tabs(["Ybus", "Zbus"])
        with tab_ybus:
            _show_dataframe(
                _matrix_display_rows(st.session_state.case, ybus, data_form),
            )
        with tab_zbus:
            zbus = st.session_state.zbus
            if zbus is None:
                st.warning("Zbus is not available for the current case.")
            else:
                st.write(f"Computed from Ybus using: `{st.session_state.zbus_method}`")
                _show_dataframe(
                    _matrix_display_rows(st.session_state.case, zbus, data_form),
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
        _show_dataframe(bus_rows)

        st.markdown("**Line Flows and Losses**")
        _show_large_table(st.session_state.line_rows)

        st.markdown("**Power Balance**")
        _show_large_table(st.session_state.balance_rows)

        st.markdown("**Iteration History**")
        _show_dataframe(st.session_state.history_rows)

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
        st.write(
            "Sequence network options: "
            f"Z0/Z1 scale={summary['branch_zero_seq_scale']:.2f}, "
            f"branch overrides={summary['branch_scale_override_count']}, "
            f"blocked Z0 branches={summary['blocked_zero_seq_count']}, "
            f"include bus shunts={summary['include_bus_shunts']}, "
            f"include line charging={summary['include_line_charging']}, "
            f"gen sequence on mBase={summary.get('sequence_on_gen_mbase', True)}"
        )
        if summary["note"]:
            st.warning(summary["note"])

        st.markdown(f"**Fault Currents ({data_form_label})**")
        _show_dataframe(current_rows)

        st.markdown("**Fault Diagnostics**")
        _show_dataframe(st.session_state.fault_rows_diagnostic)

        st.markdown(f"**Post-Fault Bus Voltages ({data_form_label})**")
        _show_dataframe(voltage_rows)

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
            available["Fault Diagnostics"] = (
                "fault_diagnostics.csv",
                _to_csv_bytes(st.session_state.fault_rows_diagnostic),
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
            summary_lines.append(f"Generator sequence data on mBase: {fs.get('sequence_on_gen_mbase', True)}")

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
