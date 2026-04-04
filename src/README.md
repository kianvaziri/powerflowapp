# Source Structure

Current implemented modules:

- `models/` - typed network data containers
- `parser/` - MATPOWER-style input parsing
- `ybus/` - Y-bus construction with line charging and tap ratio support
- `powerflow/gs/` - Gauss-Seidel solver (M2)
- `powerflow/nr/` - Newton-Raphson solver (M3)
- `validation/` - runnable validation/demo scripts

Planned next modules:

- `shortcircuit/` - fault and symmetrical component analysis
- `ui/` - web or desktop user interface
- `export/` - CSV/TXT output formatting
