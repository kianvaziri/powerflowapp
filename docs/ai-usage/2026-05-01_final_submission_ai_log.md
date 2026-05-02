# AI Usage Log Entry - Group 16 (Final Submission)

## Entry Metadata

- Date: 2026-05-01
- Contributor: Group 16
- Milestone: Final Submission (Week 15)
- Tool(s): Codex (GPT-5 coding assistant)

## Prompt Summary

- Objective:
  - Start final milestone implementation work.
  - Add final demonstration automation and artifacts.
  - Prepare final validation, report, and presentation support files.
- Key prompt(s):
  - "Can we now start work on the final milestone?"

## Generated Output Summary

- Added final demo runner:
  - `src/validation/run_final_submission_demo.py`
  - `scripts/run_final_demo.sh`
- Generated final validation artifacts under `docs/validation/`:
  - `final_ieee14_powerflow_summary.csv`
  - `final_ieee14_fault_summary.csv`
  - `final_ieee14_fault_currents.csv`
  - `final_ieee14_post_fault_voltages.csv`
  - `final_submission_summary.txt`
- Added final validation report:
  - `docs/validation/Final_submission_validation_report.md`
- Added presentation/demo artifacts:
  - `docs/presentation/final_demo_script.md`
  - `docs/presentation/final_presentation_outline.md`
- Added final report draft:
  - `docs/reports/group16_final_report_draft.md`

## Verification and Modification

- How results were checked:
  - Ran `./scripts/run_final_demo.sh --fault-bus 4 --tolerance 1e-6 --max-iterations 200`.
  - Verified PASS summary and generated CSV artifacts.
  - Ran full tests (`pytest`) to confirm no regressions.
- What was changed by the team:
  - Kept final demo focused on required IEEE-14 power flow + 3PH fault evidence.
  - Separated final demo artifacts from M1-M5 artifacts for clarity.
- Why changes were needed:
  - Final week grading requires clean, reproducible demonstration evidence and clear submission packaging.

## Final Outcome

- Files affected:
  - `src/validation/run_final_submission_demo.py`
  - `scripts/run_final_demo.sh`
  - `docs/validation/Final_submission_validation_report.md`
  - `docs/validation/final_ieee14_powerflow_summary.csv`
  - `docs/validation/final_ieee14_fault_summary.csv`
  - `docs/validation/final_ieee14_fault_currents.csv`
  - `docs/validation/final_ieee14_post_fault_voltages.csv`
  - `docs/validation/final_submission_summary.txt`
  - `docs/presentation/final_demo_script.md`
  - `docs/presentation/final_presentation_outline.md`
  - `docs/reports/group16_final_report_draft.md`
- Impact on project:
  - Establishes a reproducible final-demo workflow and submission-ready evidence baseline for Week 15.
