# Matplotlib Packaging Readiness

The Fuel Transfer Pump graph uses Matplotlib's embedded `FigureCanvasTkAgg`
backend. A future PyInstaller build must include Matplotlib and its TkAgg backend
dependencies. YSH does not use `pyplot`, external chart windows, network data, or
web resources for this visualization.
