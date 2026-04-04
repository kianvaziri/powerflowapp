# M3 NR Checklist (Week 11, 20%)

- [x] Full NR implementation complete.
- [x] Jacobian recomputed each iteration.
- [x] Mismatch vector and norm calculated.
- [x] Convergence control parameters exposed.
- [x] GS vs NR comparison documented (iterations/time).

## Evidence Links

- NR solver: `src/powerflow/nr/newton_raphson.py`
- NR demo: `src/validation/run_m3_nr_demo.py`, `scripts/run_m3_nr_demo.sh`
- GS-vs-NR comparison: `src/validation/run_m3_gs_nr_compare.py`, `scripts/run_m3_gs_nr_compare.sh`
- NR tests: `tests/powerflow/test_newton_raphson.py`
- Validation report: `docs/validation/M3_nr_validation_report.md`
- Comparison artifact: `docs/validation/m3_gs_vs_nr_comparison.csv`
