# UI Phase 1 Design System

YSH Phase 1 uses native Tkinter ttk styling rather than ttkbootstrap. The
application already uses ttk widgets extensively, so centralized `ttk.Style`
configuration provides the requested modern turquoise engineering identity with
the lowest migration risk.

The visual tokens live in `ui/theme/`: semantic colors, typography, spacing, and
style application. The Phase 1 scope applies these to the application shell,
selected calculation tabs, project sidebar, active-project card, status bar, and
project action buttons. Calculation logic, persistence, data libraries, and
formula workflows are intentionally unchanged.
