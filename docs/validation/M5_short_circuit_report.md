# M5 Validation Report: Short-Circuit Analysis

## Objective Coverage

Milestone 5 requires:
1. Three-phase fault calculation
2. Symmetrical-component-based fault analysis
3. Sequence network model
4. Generator subtransient reactance inclusion
5. Fault current and post-fault bus voltage computation
6. Fault results visible in the UI

## Implementation Summary

Implemented files:
- `src/shortcircuit/fault_analysis.py`
- `src/shortcircuit/__init__.py`
- `src/ui/streamlit_app.py`
- `src/validation/run_m5_fault_demo.py`
- `scripts/run_m5_fault_demo.sh`
- `tests/shortcircuit/test_fault_analysis.py`

### Numerical Method

- Positive, negative, and zero sequence Y-bus matrices are formed for fault analysis.
- In the absence of explicit sequence branch parameters in MATPOWER input, branch sequence parameters are approximated from the positive-sequence network.
- Generator subtransient reactance is included as shunt admittance in sequence networks (default `X''d = 0.2 p.u.` unless overridden by bus mapping).
- Fault types implemented:
  - `3PH`
  - `LG`
  - `LL`
  - `LLG`
- Post-fault phase voltages are reconstructed from sequence voltages.

## Automated Test Evidence

Command:

```bash
.venv/bin/python -m pytest -q
```

Result:
- `27 passed`

M5-specific tests:
- `tests/shortcircuit/test_fault_analysis.py`

## M5 Demonstration Artifacts

Commands:

```bash
./scripts/run_m5_fault_demo.sh --method NR --fault-bus 4
./scripts/run_m5_fault_demo.sh --method GS --fault-bus 4
```

Observed summary output:
- NR pre-fault: converged `True`, iterations `2`
- GS pre-fault: converged `True`, iterations `39`

Generated CSV artifacts:
- `docs/validation/m5_nr_fault_currents.csv`
- `docs/validation/m5_nr_post_fault_voltages.csv`
- `docs/validation/m5_gs_fault_currents.csv`
- `docs/validation/m5_gs_post_fault_voltages.csv`

## UI Integration Coverage

Run command:

```bash
./scripts/run_m4_ui.sh
```

UI now supports:
- fault type selection (`3PH`, `LG`, `LL`, `LLG`)
- fault location selection (bus)
- optional fault impedance input (`Rf`, `Xf`)
- table output for fault currents and post-fault voltages
- CSV/TXT export including fault-analysis results

## Conclusion

M5 requirements are implemented with tested sequence-network fault analysis and integrated UI display/export workflow.
