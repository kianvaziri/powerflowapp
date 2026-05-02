# Final Presentation Outline (Group 16)

## Slide 1: Title

- EE 4310 Power Systems Analysis
- Group 16
- Project: GridSolver (Power Flow + Fault Analysis)

## Slide 2: Problem Statement

- Need a practical tool for:
  - Y-bus formation
  - GS and NR power flow
  - Short-circuit analysis
- Validation target: IEEE 14-bus

## Slide 3: System Architecture

- Parser -> Validation -> Matrix builder -> Solvers -> Fault study -> UI/export
- Python implementation with Streamlit UI

## Slide 4: Power Flow Methods

- Gauss-Seidel: iterative, robust baseline
- Newton-Raphson: fast convergence via Jacobian
- Convergence tolerance set to `1e-6` p.u.

## Slide 5: Fault Analysis Method

- Symmetrical components / sequence-network approach
- Supports `3PH`, `LG`, `LL`, `LLG`
- Final demonstration requirement uses `3PH` at selected bus

## Slide 6: UI Workflow

- Top sequence buttons:
  - Load -> Validate -> Create Ybus -> Power Flow -> Fault Study -> Export
- Matrix display includes both Ybus and Zbus

## Slide 7: IEEE 14-bus Validation Evidence

- GS and NR both converge
- Show final summary table and residual/power balance values
- Highlight NR vs GS iteration difference

## Slide 8: Fault Validation Evidence

- 3PH fault at bus 4
- Show `|Ia|` and post-fault voltage outputs
- Reference exported CSV artifacts

## Slide 9: Final Deliverables

- Working app (macOS + Windows launchers)
- Final validation package
- AI usage logs
- Final report draft

## Slide 10: Lessons Learned / Q&A

- Numerical stability and data quality checks
- UI workflow design decisions
- Future improvements
