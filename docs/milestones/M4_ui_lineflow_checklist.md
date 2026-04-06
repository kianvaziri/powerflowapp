# M4 UI + Line Flow Checklist (Week 12, 15%)

- [x] UI supports loading system input file.
- [x] UI supports selecting GS/NR and solver settings.
- [x] Line power flows and losses computed.
- [x] Power balance check performed (`Pgen - Pload - Ploss - Pshunt approx 0`).
- [x] Results displayed in tables and exportable to CSV/TXT.

## Evidence Links

- UI app: `src/ui/streamlit_app.py`
- UI launcher: `scripts/run_m4_ui.sh`
- Line flow and balance implementation: `src/powerflow/line_flow.py`
- M4 artifact generator: `src/validation/run_m4_report_demo.py`, `scripts/run_m4_demo.sh`
- Line-flow tests: `tests/powerflow/test_line_flow.py`
- Validation report: `docs/validation/M4_ui_lineflow_report.md`
- Generated artifacts: `docs/validation/m4_*_*.csv`
