# EE 4310 Power Systems Analysis - Group Project (Spring 2026)

This repository is organized to match the EE 4310 project specification and grading milestones.

## Required Application Scope

The app must implement and demonstrate:

1. Y-bus matrix formation.
2. Power flow:
   - Gauss-Seidel (GS)
   - Newton-Raphson (NR)
3. Short-circuit analysis:
   - Three-phase fault
   - Symmetrical component-based fault analysis
4. UI (desktop or web) with:
   - Input file load
   - Solver/fault selection
   - Tolerance and iteration settings
   - Result display and export (CSV/TXT)

Primary validation system: IEEE 14-bus.

## Milestones (Spec-Aligned)

| Milestone | Week | Weight | Required Output |
|---|---:|---:|---|
| M0 Proposal | 7 | 5% | Team roles, stack choice, development plan |
| M1 Parser + Y-bus | 8 | 10% | Working parser, correct Y-bus, small-system validation |
| M2 Gauss-Seidel | 9 | 15% | Functional GS, convergence demonstration, iteration reporting |
| M3 Newton-Raphson | 11 | 20% | Full NR + Jacobian + GS/NR comparison |
| M4 UI + Line Flow | 12 | 15% | Functional UI, line flow/losses, export |
| M5 Short-Circuit | 14 | 20% | 3-phase + symmetrical components in UI |
| Final Submission | 15 | 15% | Working app, 6-10 page report, AI log, IEEE 14-bus demo |

Detailed checklists are in `docs/milestones/`.

## Repository Structure

```text
.github/                         # CI and GitHub templates
/docs/
  milestones/                    # Per-milestone checklists
  templates/                     # Proposal/report/AI-log templates
  ai-usage/                      # Filled AI usage log(s)
  validation/                    # IEEE-14 and fault validation evidence
  meeting-notes/                 # Team meeting notes (dated)
  reports/                       # Report drafts and final report
  spec/                          # Official project specification
/src/                            # Core implementation
/tests/                          # Unit + integration tests
/data/raw/ieee14/                # IEEE 14-bus input data
/scripts/                        # Utility scripts
```

## Team Workflow

1. Create issue for each scoped task.
2. Create branch: `feature/<task>`, `fix/<task>`, or `docs/<task>`.
3. Open PR linked to issue with milestone tag (`M0`-`M5`/`Final`).
4. Require reviewer approval before merge.
5. Update milestone checklist when task is complete.

## Current M0 Working Decision

- Preferred implementation for v1: Python solver backend + Python web UI.
- Rationale: lowest integration risk and best cross-platform collaboration speed.
- See:
  - `docs/reports/proposal.md`
  - `docs/architecture/stack_decision.md`

## Definition of Done

- Functionality implemented and reviewed via PR.
- Relevant tests pass locally and in CI.
- Numerical assumptions and equations are documented.
- Validation artifacts added under `docs/validation/`.
- If AI tools were used, log entry added in `docs/ai-usage/`.

## Project Spec

Place the course project specification in `docs/spec/` (or keep the original in root and reference it there).

## M2 Quick Run

Use these commands from repo root:

```bash
source .venv/bin/activate
python -m pytest -q
./scripts/run_m2_gs_demo.sh
```

M2 evidence files:
- `docs/milestones/M2_gs_checklist.md`
- `docs/validation/M2_gs_convergence_report.md`

## M2 Convergence Plot

Generate a PNG convergence figure from the GS iteration-history CSV:

```bash
./scripts/plot_m2_gs_history.sh
```

Output:
- `docs/validation/m2_gs_convergence.png`

## M3 Quick Run

Use these commands from repo root:

```bash
source .venv/bin/activate
python -m pytest -q
./scripts/run_m3_nr_demo.sh
./scripts/run_m3_gs_nr_compare.sh
```

M3 evidence files:
- `docs/milestones/M3_nr_checklist.md`
- `docs/validation/M3_nr_validation_report.md`
- `docs/validation/m3_nr_iteration_history.csv`
- `docs/validation/m3_gs_vs_nr_comparison.csv`

## M4 Quick Run

Use these commands from repo root:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
./scripts/run_m4_demo.sh --method NR
./scripts/run_m4_demo.sh --method GS
./scripts/run_m4_ui.sh
```

M4 evidence files:
- `docs/milestones/M4_ui_lineflow_checklist.md`
- `docs/validation/M4_ui_lineflow_report.md`
- `docs/validation/m4_nr_bus_results.csv`
- `docs/validation/m4_nr_line_flows.csv`
- `docs/validation/m4_nr_iteration_history.csv`
- `docs/validation/m4_nr_power_balance.csv`
- `docs/validation/m4_gs_bus_results.csv`
- `docs/validation/m4_gs_line_flows.csv`
- `docs/validation/m4_gs_iteration_history.csv`
- `docs/validation/m4_gs_power_balance.csv`
