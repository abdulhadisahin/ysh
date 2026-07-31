# YSH AI Handover

The active repository contains the application beneath `YSH/`, with domain
models in `YSH/core`, SQLite schema definitions in `YSH/database`, persistence
repositories in `YSH/repositories`, service workflows in `YSH/services`, and
Tkinter ttk UI in `YSH/ui`.

Python 3.14 is the required runtime. Epic 6, Material and Engineering Data
Library, is complete. The current test command is:

```powershell
"C:\Users\USER\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pytest .\YSH\tests -v --basetemp .\work\pytest-epic6 -p no:cacheprovider
```

Latest passing-test count: 96. The next planned Epic has not been specified.
PDF reporting is outside scope unless explicitly reintroduced. YSH is a
single-user, local, fully offline Windows desktop application; multi-user and
network operation are outside scope.
