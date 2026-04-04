# M3 Validation Report: Newton-Raphson Power Flow

## Objective Coverage

Milestone 3 requires:
1. Complete NR solver
2. Jacobian implementation with per-iteration update
3. Mismatch vector and convergence norm
4. Exposed convergence controls
5. GS vs NR comparison

## Implementation Summary

Implemented files:
- `src/powerflow/nr/newton_raphson.py`
- `src/powerflow/nr/__init__.py`
- `src/validation/run_m3_nr_demo.py`
- `src/validation/run_m3_gs_nr_compare.py`
- `scripts/run_m3_nr_demo.sh`
- `scripts/run_m3_gs_nr_compare.sh`

The solver uses polar-form NR with state vector:
- voltage angles for non-slack buses
- voltage magnitudes for PQ buses

### Jacobian and Mismatch

At each iteration, the solver:
1. Computes active/reactive mismatch vector (`ΔP`, `ΔQ`)
2. Rebuilds full Jacobian blocks (`H`, `N`, `M`, `L`)
3. Solves `J * dx = mismatch`
4. Updates state and recomputes post-update mismatch

Iteration history tracks:
- `max_power_mismatch`
- `max_state_update`
- `jacobian_size`

## Automated Test Evidence

Command:

```bash
.venv/bin/python -m pytest -q
```

Result:
- `19 passed`

NR-specific tests:
- `tests/powerflow/test_newton_raphson.py`

## IEEE-14 NR Convergence Demonstration

Command:

```bash
./scripts/run_m3_nr_demo.sh
```

Observed output:
- Converged: `True`
- Iterations: `2`
- Final max mismatch: `1.315804e-10`
- Final max state update: `2.264672e-06`

Generated file:
- `docs/validation/m3_nr_iteration_history.csv`

## GS vs NR Comparison

Command:

```bash
./scripts/run_m3_gs_nr_compare.sh
```

Generated file:
- `docs/validation/m3_gs_vs_nr_comparison.csv`

Observed comparison:
- GS: converged `True`, iterations `39`, final max mismatch `9.904314760001e-07`
- NR: converged `True`, iterations `2`, final max mismatch `1.315804479263e-10`

## Conclusion

M3 requirements are implemented and validated:
- NR solver is complete
- Jacobian is rebuilt each iteration
- mismatch/norm tracking is present
- convergence controls are exposed
- GS-vs-NR comparison is documented and reproducible
