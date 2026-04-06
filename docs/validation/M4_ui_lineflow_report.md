# M4 Validation Report: UI + Line Flow + Export

## Objective Coverage

Milestone 4 requires:
1. Functional UI with input loading and solver settings
2. Line-flow and line-loss calculations
3. Power-balance checking
4. Export of results to CSV/TXT

## Implementation Summary

Implemented files:
- `src/powerflow/line_flow.py`
- `src/ui/streamlit_app.py`
- `src/validation/run_m4_report_demo.py`
- `scripts/run_m4_ui.sh`
- `scripts/run_m4_demo.sh`
- `tests/powerflow/test_line_flow.py`

### Line Flow / Loss Method

For each in-service branch, complex line currents and powers are computed from solved bus voltages using the same branch model as Y-bus stamping (series admittance, half-line charging, tap ratio/angle). Reported per branch:
- `P_from`, `Q_from`
- `P_to`, `Q_to`
- `P_loss = P_from + P_to`
- `Q_loss = Q_from + Q_to`

### Power Balance Method

Balance terms are computed from solved voltages and Y-bus injections:
- estimated total generation (`P_generation_est`, `Q_generation_est`)
- total load (`P_load`, `Q_load`)
- branch losses (`P_branch_loss`, `Q_branch_loss`)
- bus-shunt injection term (`P_bus_shunt_injection`, `Q_bus_shunt_injection`)

Balance residuals:
- `P_balance = P_generation_est - P_load - P_branch_loss - P_bus_shunt_injection`
- `Q_balance = Q_generation_est - Q_load - Q_branch_loss - Q_bus_shunt_injection`

## Automated Test Evidence

Command:

```bash
.venv/bin/python -m pytest -q
```

Result:
- `22 passed`

M4-specific tests:
- `tests/powerflow/test_line_flow.py`

## M4 Demonstration Artifacts

Commands:

```bash
./scripts/run_m4_demo.sh --method NR
./scripts/run_m4_demo.sh --method GS
```

Observed summary output:
- NR: converged `True`, iterations `2`, `P_balance=-4.618528e-14`, `Q_balance=-1.065814e-12`
- GS: converged `True`, iterations `39`, `P_balance=5.329071e-14`, `Q_balance=-1.062261e-12`

Generated CSV artifacts:
- `docs/validation/m4_nr_bus_results.csv`
- `docs/validation/m4_nr_line_flows.csv`
- `docs/validation/m4_nr_iteration_history.csv`
- `docs/validation/m4_nr_power_balance.csv`
- `docs/validation/m4_gs_bus_results.csv`
- `docs/validation/m4_gs_line_flows.csv`
- `docs/validation/m4_gs_iteration_history.csv`
- `docs/validation/m4_gs_power_balance.csv`

## UI Run Command

```bash
./scripts/run_m4_ui.sh
```

The UI supports:
- bundled case selection or uploaded `.m` file
- GS/NR selection
- tolerance and max-iteration settings
- tabular display of voltages, flows, history, and balance
- CSV and TXT download buttons

## Conclusion

M4 requirements are implemented, tested, and documented with reproducible artifacts.
