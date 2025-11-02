# taskmgr White‑box Test Plan (mapping to code units & branches)

Summary
- Purpose: exercise internal logic paths: command parsing, argument count checks, type validation, date parsing, repeat/prio validation, id lookup, sorting comparator, case-insensitive matching, automatic fields (done, ctime, id).
- Assumptions/Notes:
  - The specification text has a conflict: Description says default priority is MEDIUM, while add's Arguments section says default LOW. White‑box tests include both checks; confirm which is correct.
  - The spec mentions "delete" but no concrete command syntax. I assumed a potential "delete" command of the forms:
      - delete id=<id>
      - delete property=<prop> val=<val>
    Do you want delete tests? I did not include delete white‑box tests until syntax is confirmed.

Unit/Module targets and test vectors
1) Parser: parse_command(line)
  - Branches to cover:
    - Recognize valid command names: help, print, add, list, mod, done
    - Unknown command -> InvalidArgument
    - Argument tokenization: handle spaces, equals, quoted strings, extra spaces
    - Argument count validation per command
    - Argument type detection (strings vs integers)
  - Tests:
    - P-1: Valid add with quoted strings -> parse succeeds, returns command name and arg map
    - P-2: add missing required arg (name) -> parser signals MissingArguments
    - P-3: Too many args for add -> TooManyArguments
    - P-4: Non‑string arg where string expected (e.g., name=12345 without quotes) -> InvalidArgumentType
    - P-5: Line >1024 chars -> branch handling (reject or accept) — test boundary 1024 and 1025

2) Validator: validate_args(command, args)
  - Branches:
    - Date format acceptance DD-MM-YYYY -> valid vs invalid
    - Repeat enumeration (NONE, DAILY, WEEKLY, MONTHLY)
    - Priority enumeration (LOW, MEDIUM, HIGH)
    - Done value for mod (True/False)
  - Tests:
    - V-1: Valid date "31-12-2025" -> accepted
    - V-2: Invalid date "31/12/2025" -> InvalidDateFormat
    - V-3: rep "DAILY" accepted; "YEARLY" rejected -> InvalidRepeat
    - V-4: prio "HIGH" accepted; "URGENT" rejected -> InvalidPriority
    - V-5: done "True"/"False" accepted; "yes" rejected -> InvalidDoneStatus

3) Storage/state: add_task, mod_task, done_task
  - Branches:
    - ID assignment path (first id=0)
    - Duplicate ids cannot happen (atomic increment)
    - Task not found -> TaskNotFound
    - Modifying computed fields (done, id, ctime) should be protected (done must be modifiable only via done command)
  - Tests:
    - S-1: add_task increments id from 0 sequentially
    - S-2: mod_task id nonexistent -> TaskNotFound
    - S-3: done_task toggles done True and cannot set invalid values

4) Listing & Sorting: list_tasks / print
  - Branches:
    - Filtering by property (case-insensitive)
    - Sorting by different properties: name, due, prio, type, id, ctime
    - Direction asc/desc
    - Invalid sort_by -> InvalidArgument
    - Invalid direction -> InvalidArgument
  - Tests:
    - L-1: list filters case-insensitively
    - L-2: sort_by due sorts by date correctly (dates must be parsed to comparable form)
    - L-3: sort_by prio must follow priority order (LOW < MEDIUM < HIGH) or lexicographic? Spec implies enumerated order — confirm expected ordering; tests assume HIGH > MEDIUM > LOW
    - L-4: print with default sort_by and direction (name asc)

5) Output messages:
  - Branches:
    - Command success message format
    - Error messages format "Error <Type>: <command>"
  - Tests:
    - O-1: On success, exact "Command success: <command>" printed
    - O-2: On error, exact "Error <Type>: <command>" printed

6) Time stamping: ctime generation
  - Branches: presence of ctime on creation; accuracy up to seconds
  - Tests:
    - T-1: add_task creates ctime; verify format and that it is <= current time and > current time - 5s (approx)

7) Edge cases:
  - Empty strings for optional fields
  - Maximum name length not specified — test very long name (near 1024) versus line limit
  - Missing delete command: flagged for clarification

Suggested code unit tests (pytest style) are provided in test_taskmgr.py file included below.

If you want, I can:
- Produce a mapping matrix (requirements → test cases)
- Generate Gherkin .feature files for the black‑box scenarios
- Build runnable pytest tests against your code when you provide the repository or function signatures
