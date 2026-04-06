# AI Usage Log Entry - Group 16 (M4)

## Entry Metadata

- Date: 2026-04-03
- Contributor: Group 16
- Milestone: M4 (UI + Line Flow + Export)
- Tool(s): Codex (GPT-5 coding assistant)

## Prompt Summary

- Objective:
  - Start Milestone 4 implementation.
  - Add UI workflow for loading cases, choosing GS/NR, and running analysis.
  - Compute line flows/losses and add power-balance reporting.
  - Export reproducible CSV/TXT outputs.
- Key prompt(s):
  - Start M4 implementation now.

## Generated Output Summary

- Added M4 line-flow and system-balance module.
- Added Streamlit-based UI for case loading, solver execution, and result tables.
- Added M4 artifact generator script and shell launcher scripts.
- Added M4 tests for branch flow and balance behavior.
- Added M4 milestone checklist and validation report.

## Verification and Modification

- How results were checked:
  - Ran full project test suite with `pytest`.
  - Ran M4 demo for NR and GS to generate CSV artifacts.
  - Checked balance residuals and iteration history outputs.
- What was changed by the team:
  - Refined balance equations to include bus-shunt term so residuals are physically consistent.
  - Removed pandas dependency from report script path to reduce setup overhead.
- Why changes were needed:
  - Ensure M4 evidence is reproducible with current project environment.

## Final Outcome

- Files affected:
  - `src/powerflow/line_flow.py`
  - `src/ui/streamlit_app.py`
  - `src/validation/run_m4_report_demo.py`
  - `scripts/run_m4_ui.sh`
  - `scripts/run_m4_demo.sh`
  - `tests/powerflow/test_line_flow.py`
  - `docs/milestones/M4_ui_lineflow_checklist.md`
  - `docs/validation/M4_ui_lineflow_report.md`
- Impact on project:
  - M4 requirements are implemented, tested, and documented with generated validation artifacts.
