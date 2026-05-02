# Final Submission Validation Report

Date: 2026-05-01  
Course: EE 4310 Power Systems Analysis  
Team: Group 16

## Scope

This report provides final-submission evidence for the Week 15 requirements:

- Complete working application
- IEEE 14-bus power-flow demonstration
- Correct three-phase fault current demonstration at a selected bus
- Reasonable convergence tolerance (`1e-6` p.u.)

## Validation Command

```bash
./scripts/run_final_demo.sh --fault-bus 4 --tolerance 1e-6 --max-iterations 200
```

The command generates:

- `docs/validation/final_ieee14_powerflow_summary.csv`
- `docs/validation/final_ieee14_fault_summary.csv`
- `docs/validation/final_ieee14_fault_currents.csv`
- `docs/validation/final_ieee14_post_fault_voltages.csv`
- `docs/validation/final_submission_summary.txt`

## Results Summary

From `final_ieee14_powerflow_summary.csv`:

- GS converged: `True` in `39` iterations
- NR converged: `True` in `2` iterations
- Tolerance used: `1e-6` p.u.
- Power-balance residuals are near machine precision for both methods

From `final_ieee14_fault_summary.csv`:

- Fault type: `3PH`
- Fault bus: `4`
- Pre-fault solver used: `NR` (converged)
- Fault current magnitude: `|Ia| = 12.114768` p.u.

From `final_submission_summary.txt`:

- Reasonable tolerance check (`<=1e-6`): `True`
- Overall status: `PASS`

## Requirement Mapping

| Final requirement | Evidence |
|---|---|
| Working application | UI module + launcher scripts (`Launch_PowerFlow_UI.command`, `WindowsLauncher_PowerFlow_UI.bat`) |
| IEEE 14-bus power flow | `final_ieee14_powerflow_summary.csv` |
| 3PH fault current at selected bus | `final_ieee14_fault_summary.csv`, `final_ieee14_fault_currents.csv` |
| Reasonable convergence tolerance | `final_submission_summary.txt` (`1e-6`, PASS) |

## Conclusion

Final validation artifacts confirm that Group 16 can demonstrate the required Week 15 behavior on IEEE 14-bus with both power-flow methods and three-phase short-circuit analysis at a selected bus.
