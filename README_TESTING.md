Testing taskmgr
================

This folder contains helper files to run manual blackbox tests for `taskmgr`.

Files added:
- `blackbox_commands.txt` — full command file (commented) extracted from the provided CSV tests. Run `taskmgr` on this file to execute all tests in order.
- `commands_paste.txt` — plain command lines only (no comments). You can copy/paste these directly into a terminal (one per line).
- `commands_success.txt` — only the commands expected to succeed.
- `commands_fail.txt` — only the commands expected to produce errors.
- `run_blackbox.ps1` — PowerShell helper script that runs `taskmgr` on `blackbox_commands.txt` and writes `blackbox_results.txt`.

How to run (PowerShell):

1. From the project folder:

```powershell
Set-Location -Path 'D:\files (1)'
python .\taskmgr.py .\blackbox_commands.txt
```

2. Or use the helper script which also saves results:

```powershell
Set-Location -Path 'D:\files (1)'
.\run_blackbox.ps1
```

3. If you want to copy commands and paste them directly into an interactive shell, open `commands_paste.txt` and paste lines one by one.

Notes:
- `blackbox_commands.txt` includes one intentionally very long line (>1024 chars) to exercise the `TooLongLine` behavior.
- Lines starting with `#` are comments and are skipped by `taskmgr`.
