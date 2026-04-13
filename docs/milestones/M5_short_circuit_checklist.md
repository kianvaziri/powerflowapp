# M5 Short-Circuit Checklist (Week 14, 20%)

- [x] Three-phase fault calculation implemented.
- [x] Symmetrical component formulation implemented.
- [x] Sequence network model included.
- [x] Generator subtransient reactances included.
- [x] Fault current and post-fault bus voltages computed.
- [x] Fault analysis results viewable in UI.

## Evidence Links

- Short-circuit module: `src/shortcircuit/fault_analysis.py`
- Short-circuit exports: `src/shortcircuit/__init__.py`
- UI integration: `src/ui/streamlit_app.py`
- M5 demo script: `src/validation/run_m5_fault_demo.py`, `scripts/run_m5_fault_demo.sh`
- M5 tests: `tests/shortcircuit/test_fault_analysis.py`
- M5 validation report: `docs/validation/M5_short_circuit_report.md`
- Generated artifacts: `docs/validation/m5_*_*.csv`
