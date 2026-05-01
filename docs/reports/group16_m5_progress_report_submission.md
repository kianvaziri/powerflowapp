# Group 16 - Milestone 5 Progress Report

**Course:** EE 4310 - Power Systems Analysis  
**Milestone:** M5 (Short-Circuit Analysis)  
**Students:** Maria Gonzalez, Brian Ramirez, Kian Vaziri  
**Instructor:** Arash Jamebozorg  
**Date:** April 13, 2026

## 1. Objective
Milestone 5 requires implementation and demonstration of:

1. Three-phase fault analysis
2. Symmetrical-component-based fault analysis
3. Sequence-network modeling
4. Generator subtransient reactance inclusion
5. Fault current and post-fault bus voltage computation
6. Fault analysis display in the UI

## 2. Implementation Summary
M5 functionality has been implemented and integrated into the existing app.

Implemented components:
- Short-circuit analysis core module: `src/shortcircuit/fault_analysis.py`
- Short-circuit exports: `src/shortcircuit/__init__.py`
- UI integration for fault analysis: `src/ui/streamlit_app.py`
- Validation/demo runner: `src/validation/run_m5_fault_demo.py`
- Shell launcher: `scripts/run_m5_fault_demo.sh`
- Automated tests: `tests/shortcircuit/test_fault_analysis.py`

## 3. Numerical Method

### 3.1 Sequence-Network Modeling
The implementation builds positive, negative, and zero-sequence networks and uses sequence-domain fault equations.

### 3.2 Generator Subtransient Reactance
Generator subtransient reactance is included as sequence-network shunt admittance. A default value (`X''d = 0.2 p.u.`) is used unless overridden by bus-based maps.

### 3.3 Fault Types Implemented
The following fault types are implemented:
- `3PH` (three-phase, balanced)
- `LG` (single line-to-ground)
- `LL` (line-to-line)
- `LLG` (double line-to-ground)

### 3.4 Post-Fault Quantities
For each fault run, the app computes:
- sequence currents (`I0`, `I1`, `I2`)
- phase currents (`Ia`, `Ib`, `Ic`)
- post-fault phase voltages per bus (`Va`, `Vb`, `Vc`)

## 4. UI Integration
The Streamlit interface now supports full M5 interaction:
- fault type selection
- fault location (bus) selection
- fault impedance input (`Rf`, `Xf`)
- tabular fault current output
- tabular post-fault bus-voltage output
- CSV/TXT export including fault-analysis results

Run command:

```bash
./scripts/run_m4_ui.sh
```

## 5. Validation and Test Results

### 5.1 Automated Tests
Command:

```bash
.venv/bin/python -m pytest -q
```

Result:
- `27 passed`

### 5.2 M5 Demonstration Runs
Commands:

```bash
./scripts/run_m5_fault_demo.sh --method NR --fault-bus 4
./scripts/run_m5_fault_demo.sh --method GS --fault-bus 4
```

Observed pre-fault convergence:
- NR: converged `True`, iterations `2`
- GS: converged `True`, iterations `39`

Generated M5 artifacts:
- `docs/validation/m5_nr_fault_currents.csv`
- `docs/validation/m5_nr_post_fault_voltages.csv`
- `docs/validation/m5_gs_fault_currents.csv`
- `docs/validation/m5_gs_post_fault_voltages.csv`

## 6. Requirement Status Matrix

| M5 Requirement | Status |
|---|---|
| Three-phase fault calculation | Complete |
| Symmetrical component formulation | Complete |
| Sequence network model | Complete |
| Generator subtransient reactances | Complete |
| Fault current and post-fault voltages | Complete |
| Fault analysis results viewable in UI | Complete |

## 7. Figure Placeholders
- **Figure 1.** M5 sidebar controls (fault type, location, `Rf`, `Xf`).  
  _[Insert screenshot]_  
- **Figure 2.** Fault current output table (`I0`, `I1`, `I2`, `Ia`, `Ib`, `Ic`).  
  _[Insert screenshot]_  
- **Figure 3.** Post-fault bus voltage table (`Va`, `Vb`, `Vc`).  
  _[Insert screenshot]_  
- **Figure 4.** Export controls including fault CSV outputs.  
  _[Insert screenshot]_

## 8. Conclusion
Milestone 5 requirements are implemented, tested, and integrated into the UI. Group 16 now has a working short-circuit analysis workflow that supports multiple fault types, reports fault currents and post-fault voltages, and exports reproducible artifacts for validation and reporting.
