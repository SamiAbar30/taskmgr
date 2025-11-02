```markdown
# taskmgr

Command-driven task manager implemented in Python.

Usage:
    python3 taskmgr.py <input-file>

Input file:
- Lines are commands (one command per line).
- Lines starting with `#` are comments.
- Commands: help, print, add, list, mod, done
- Arguments have the form: key="value" (quotes optional for some tokens)

Notes:
- Default priority chosen: MEDIUM (the provided spec had a conflict; tests are aligned to MEDIUM).
- The program prints success messages: `Command success: <command>`
- On errors it prints: `Error <ErrorType>: <command>`
- Commands longer than 1024 characters will raise an error.

Run tests:
- pytest is required. From repo root:
    pytest -q

Files:
- taskmgr.py : the application
- tests/test_taskmgr.py : pytest test suite
- blackbox_tests.csv : black-box acceptance test cases
- features/taskmgr.feature : Gherkin scenarios
```