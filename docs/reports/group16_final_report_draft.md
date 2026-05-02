# Group 16 Final Technical Report Draft

Course: EE 4310 Power Systems Analysis  
Instructor: Arash Jamebozorg  
Team: Group 16  
Date: 2026-05-01

## 1. Introduction

This project delivers a full power-system analysis workflow that combines classical steady-state power-flow methods with short-circuit fault analysis in a usable interface. The target problem is to build and validate a practical application that can:

- Parse MATPOWER-style case files
- Form the Y-bus matrix
- Solve power flow using both Gauss-Seidel (GS) and Newton-Raphson (NR)
- Compute line flows, losses, and power balance
- Perform symmetrical-component-based short-circuit analysis
- Present and export results through a guided UI workflow

The IEEE 14-bus system is used as the primary validation case for all final demonstrations.

## 2. Problem Formulation

### 2.1 Network Model

The system is represented by buses, branches, and generators parsed from MATPOWER-style input data. Bus power injections and branch admittances are converted into a nodal admittance matrix (Y-bus), which is the core model used by both power-flow and fault analysis modules.

### 2.2 Per-Unit and Convergence Settings

All calculations are performed in per-unit quantities with tolerance-driven iterative convergence. For final submission demonstrations, tolerance is set to `1e-6` p.u., matching the course guidance for a reasonable convergence threshold.

### 2.3 Fault Model

Short-circuit analysis uses sequence-network methods. Positive-, negative-, and zero-sequence networks are assembled and connected according to fault type (`3PH`, `LG`, `LL`, `LLG`). For the final required demonstration, a three-phase fault is evaluated at a selected bus in the IEEE 14-bus case.

## 3. Methods

### 3.1 Parser and Data Validation

The parser extracts bus, generator, and branch matrices from case files. Validation checks enforce workflow correctness before solving:

- Slack-bus existence and consistency
- Bus numbering sanity and uniqueness
- Branch data checks (references, impedance, taps, duplicates)
- Generator consistency checks

These checks are surfaced in the UI during the `Validate` step and block progression when critical errors are present.

### 3.2 Y-bus and Z-bus Construction

Y-bus is formed from branch and shunt contributions with transformer tap handling. The UI also displays a Z-bus matrix for interpretability and fault-study context. Z-bus is computed as the inverse of Y-bus when invertible, with pseudo-inverse fallback when needed for numerical robustness.

### 3.3 Gauss-Seidel (GS) Power Flow

GS iteratively updates bus voltages until mismatch criteria are met or iteration limits are reached. It serves as a transparent baseline solver and a useful comparison point for NR performance.

### 3.4 Newton-Raphson (NR) Power Flow

NR solves the nonlinear power-flow equations using Jacobian-based state updates. In this project it converges faster than GS on IEEE 14-bus while maintaining high numerical accuracy.

### 3.5 Line Flow and Power Balance

After voltage convergence, branch-level complex power flows and total balance metrics are computed. These outputs are used to verify physically consistent results and are included in UI tables and CSV exports.

### 3.6 Short-Circuit Analysis

Fault analysis computes sequence currents and phase-domain post-fault voltages. The implementation supports:

- `3PH` (three-phase)
- `LG` (single line-to-ground)
- `LL` (line-to-line)
- `LLG` (double line-to-ground)

Final-week requirement evidence focuses on correct `3PH` fault-current output at a selected bus.

## 4. Software Design and UI Workflow

### 4.1 Architecture

The codebase is modular:

- `src/parser/` for case ingestion
- `src/ybus/` for matrix formation
- `src/powerflow/` for GS/NR and line-flow computations
- `src/shortcircuit/` for sequence-network fault analysis
- `src/ui/` for Streamlit workflow and exports
- `src/validation/` and `scripts/` for reproducible milestone/final artifacts

### 4.2 UI Design

The application enforces an operation order through top-level action buttons:

`Load File -> Validate -> Create Ybus -> Power Flow -> Fault Study -> Export`

Step gating ensures users cannot run downstream operations with stale or invalid state. Export now supports checkbox-based dataset selection with one final export action that writes to timestamped folders.

### 4.3 Cross-Platform Launch

- macOS launcher: `Launch_PowerFlow_UI.command`
- Windows launcher: `WindowsLauncher_PowerFlow_UI.bat`

Both launchers create environments, install dependencies, and start the UI with minimal setup friction.

## 5. Validation and Results

### 5.1 Test and Validation Workflow

Validation combines:

- Automated tests (`pytest`)
- Milestone evidence scripts
- Final integrated demo script for IEEE 14-bus power flow and fault validation

Final demo command:

```bash
./scripts/run_final_demo.sh --fault-bus 4 --tolerance 1e-6 --max-iterations 200
```

### 5.2 IEEE 14-Bus Power-Flow Evidence

From `docs/validation/final_ieee14_powerflow_summary.csv`:

- GS converged: `True` in `39` iterations
- NR converged: `True` in `2` iterations
- Tolerance: `1e-6` p.u.
- Power-balance residuals: near zero for both methods

This satisfies the final testing expectation for correct IEEE 14-bus power-flow behavior.

### 5.3 Three-Phase Fault Evidence

From `docs/validation/final_ieee14_fault_summary.csv`:

- Fault type: `3PH`
- Fault bus: `4`
- Pre-fault solver: `NR` (converged)
- Fault-current magnitude: `|Ia| = 12.114768` p.u.

This satisfies the final testing expectation for correct three-phase fault current at a selected bus.

### 5.4 Final Status

From `docs/validation/final_submission_summary.txt`:

- GS convergence: pass
- NR convergence: pass
- Tolerance check (`<=1e-6`): pass
- Overall status: `PASS`

## 6. Discussion

### 6.1 Convergence Behavior

The project preserves both solver paths for educational value:

- GS provides iterative transparency but can require many iterations
- NR converges rapidly on IEEE 14-bus for the same tolerance target

The side-by-side availability in both validation scripts and UI helps illustrate algorithmic tradeoffs.

### 6.2 Numerical and Modeling Assumptions

The short-circuit module uses practical assumptions when full sequence data is not available in input cases. These assumptions are documented and made explicit in code and validation reports. The structure allows future replacement with richer sequence datasets without major architectural changes.

### 6.3 Usability and Workflow Reliability

Recent UI updates focused on practical classroom/demo robustness:

- Strict operation gating
- Clear status progression
- Matrix visibility (Y-bus and Z-bus)
- Single-action export workflow
- Platform launchers for macOS and Windows

These decisions reduce demo risk and make handoff between team members smoother.

## 7. AI-Assisted Development Summary

AI assistance was used as a coding and packaging accelerator across milestones. For final submission, AI support helped generate:

- Final integrated demo automation
- Final validation artifacts and report scaffolding
- Presentation/demo scripts
- UI and launcher refinements for reliability

All AI-assisted outputs were reviewed, tested, and integrated with team-owned decisions and acceptance criteria. AI usage logs are maintained under `docs/ai-usage/`.

## 8. Conclusion

Group 16 has implemented a complete, validated power-system analysis application aligned with course requirements. The final package demonstrates:

- Correct IEEE 14-bus power-flow operation (GS and NR)
- Correct three-phase fault-current demonstration at a selected bus
- Working UI workflow with export and matrix visibility
- Reproducible validation scripts and documentation artifacts

The project is prepared for final demonstration and presentation, with clear traceability from requirements to outputs.

## References

1. EE 4310 Project Specification (Spring 2026), `docs/spec/Project Spec.rtf`  
2. MATPOWER case format conventions  
3. Repository validation artifacts under `docs/validation/`
