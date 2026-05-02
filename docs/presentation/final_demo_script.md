# Final Demo Script (Group 16)

## Demo Goal

Show end-to-end operation on IEEE 14-bus:

1. Load case
2. Validate data
3. Build Ybus / view Zbus
4. Run power flow (GS and NR)
5. Run 3PH fault study at selected bus
6. Export selected outputs

## Live Steps

1. Start the app.
   - macOS: `./Launch_PowerFlow_UI.command`
   - Windows: `WindowsLauncher_PowerFlow_UI.bat`
2. In the app:
   - Select `IEEE 14-bus`
   - Click `Load File`
3. Click `Validate`.
   - Show that checks run (slack bus, numbering, branch/generator consistency).
4. Click `Create Ybus`.
   - Show matrix tabs: `Ybus` and `Zbus`.
5. Click `Power Flow` with `NR`.
   - Point out convergence and iterations.
   - Show bus voltages, line flows/losses, and power balance.
6. Change solver to `GS` and run again.
   - Highlight convergence/iteration difference vs NR.
7. Configure fault panel:
   - Fault type: `3PH`
   - Faulted element: `Bus`
   - Faulted bus: `4`
   - `Rf = 0`, `Xf = 0`
8. Click `Fault Study`.
   - Show fault current table and post-fault voltages.
9. Click top `Export`.
   - Select desired datasets with checkboxes.
   - Set export label.
   - Click bottom `Export` button to create timestamped folder under `exports/`.

## Backup CLI Demo (if UI issues occur)

```bash
python -m pytest -q
./scripts/run_final_demo.sh --fault-bus 4 --tolerance 1e-6 --max-iterations 200
```

Show:

- `docs/validation/final_ieee14_powerflow_summary.csv`
- `docs/validation/final_ieee14_fault_summary.csv`
- `docs/validation/final_submission_summary.txt`
