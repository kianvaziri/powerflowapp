# Test Scope

Minimum expected tests:

- Parser correctness for valid/invalid inputs
- Y-bus correctness on small known systems
- GS convergence and bus-type handling
- NR Jacobian/mismatch and convergence behavior
- GS vs NR result consistency checks
- Line flow/loss and power-balance checks
- Three-phase and symmetrical component fault result checks

Current implemented test suites:

- `tests/parser/test_matpower_parser.py`
- `tests/ybus/test_build_ybus.py`
- `tests/validation/test_small_case_validation.py`
- `tests/validation/test_m2_history_export.py`
- `tests/powerflow/test_gauss_seidel.py`
- `tests/powerflow/test_newton_raphson.py`
- `tests/powerflow/test_line_flow.py`
