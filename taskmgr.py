#!/usr/bin/env python3
"""
taskmgr - Command-driven task manager
Usage: taskmgr <input-file>

Implements commands: help, print, add, list, mod, done
Prints output to stdout. Error/success messages follow the spec:
- On success: Command success: <command>
- On error:   Error <ErrorType>: <command>
"""

import sys
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional

# --- Configuration / Enums ---
PRIORITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
VALID_PRIOS = set(PRIORITY_ORDER.keys())
VALID_REPS = {"NONE", "DAILY", "WEEKLY", "MONTHLY"}
VALID_DIRECTION = {"asc", "desc"}
# Default priority choice: MEDIUM (see spec conflict note)
DEFAULT_PRIORITY = "MEDIUM"
DEFAULT_REP = "NONE"
DEFAULT_DUE = "NONE"

# Allowed property names (Note 1)
PROPERTIES = ["name", "type", "desc", "due", "rep", "prio", "done", "ctime", "id"]

# --- Error classes (internal) ---
class TaskMgrError(Exception):
    pass

class TooManyArguments(TaskMgrError): pass
class InvalidArgument(TaskMgrError): pass
class InvalidArgumentType(TaskMgrError): pass
class MissingArguments(TaskMgrError): pass
class InvalidDateFormat(TaskMgrError): pass
class InvalidRepeat(TaskMgrError): pass
class InvalidPriority(TaskMgrError): pass
class TaskNotFound(TaskMgrError): pass
class InvalidDoneStatus(TaskMgrError): pass
class UnknownCommand(TaskMgrError): pass
class TooLongLine(TaskMgrError): pass

# --- In-memory storage ---
_tasks: List[Dict[str, Any]] = []
_next_id = 0

def clear_state():
    global _tasks, _next_id
    # mutate the existing list object so external references (tests importing
    # `_tasks`) observe the cleared state instead of keeping a stale reference.
    _tasks.clear()
    _next_id = 0

# --- Utilities ---
def now_ctime_str() -> str:
    dt = datetime.now()
    # format similar to examples: day-month-year HH:MM:SS without forcing leading zeros on day/month
    return f"{dt.day}-{dt.month}-{dt.year} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"

def parse_date_str(s: str) -> Optional[date]:
    if s == "NONE":
        return None
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(\d{4})", s)
    if not m:
        raise InvalidDateFormat()
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(year, month, day)
    except Exception:
        raise InvalidDateFormat()

def format_due_for_print(due: Optional[date]) -> str:
    return due.strftime("%d-%m-%Y") if due is not None else "NONE"

def parse_bool_str(s: str) -> bool:
    if s == "True" or s == "true":
        return True
    if s == "False" or s == "false":
        return False
    raise InvalidDoneStatus()

def is_string_token_quoted(original_segment: str) -> bool:
    return '"' in original_segment or "'" in original_segment

# --- Parsing commands ---
ARG_PAIR_RE = re.compile(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))')

def tokenize_args_segment(segment: str) -> Dict[str, str]:
    """
    Extract key=value pairs. Values can be quoted or unquoted.
    Returns dict of key -> raw string value (no surrounding quotes).
    Raises InvalidArgumentType if duplicates or unknown token formats.
    """
    args = {}
    pos = 0
    for m in ARG_PAIR_RE.finditer(segment):
        key = m.group(1)
        val = m.group(2) if m.group(2) is not None else (m.group(3) if m.group(3) is not None else m.group(4))
        args[key] = val
        pos = m.end()
    # check for stray non-whitespace text after last match
    trailing = segment[pos:].strip()
    if trailing:
        # stray tokens -> treat as invalid argument or too many arguments in higher-level
        # raise InvalidArgument for unknown tokenization
        raise InvalidArgument()
    return args

# --- Command handlers ---
def cmd_help(args: Dict[str, str], original: str):
    # print each command on a new line with available args (brief)
    print("Command success: " + original)
    print("help")
    print("print [sort_by=<prop>] [direction=<asc|desc>]")
    print("add name=<name> [type=<type>] [desc=<desc>] [due=<DD-MM-YYYY>] [rep=<NONE|DAILY|WEEKLY|MONTHLY>] [prio=<LOW|MEDIUM|HIGH>]")
    print("list property=<prop> val=<value> [sort_by=<prop>] [direction=<asc|desc>]")
    print("mod id=<id> property=<prop> new_val=<value>")
    print("done id=<id>")
    print("delete id=<id> | delete property=<prop> val=<value>")
    return

def validate_sort_args(args: Dict[str, str]):
    sort_by = args.get("sort_by", "name")
    direction = args.get("direction", "asc")
    if direction not in VALID_DIRECTION:
        raise InvalidArgument()
    if sort_by not in PROPERTIES:
        raise InvalidArgument()
    return sort_by, direction

def cmd_print(args: Dict[str, str], original: str):
    # Allowed args: sort_by, direction
    # Too many args -> if any key not in allowed set
    allowed = {"sort_by", "direction"}
    for k in args.keys():
        if k not in allowed:
            raise TooManyArguments()
    sort_by, direction = validate_sort_args(args)
    # print success then content
    print("Command success: " + original)
    print_header_and_tasks(_tasks, sort_by, direction)
    return

def cmd_add(args: Dict[str, str], original: str):
    global _next_id
    allowed = {"name", "type", "desc", "due", "rep", "prio"}
    for k in args.keys():
        if k not in allowed:
            raise TooManyArguments()
    if "name" not in args:
        raise MissingArguments()
    name = args["name"]
    if name.isdigit():
        # treat unquoted purely numeric name as invalid argument type (spec)
        raise InvalidArgumentType()
    typ = args.get("type", "NONE")
    desc = args.get("desc", "")
    due_str = args.get("due", DEFAULT_DUE)
    rep = args.get("rep", DEFAULT_REP)
    prio = args.get("prio", DEFAULT_PRIORITY)
    # validate enumerations and formats
    if rep not in VALID_REPS:
        raise InvalidRepeat()
    if prio not in VALID_PRIOS:
        raise InvalidPriority()
    # validate date format
    try:
        if due_str != "NONE":
            parse_date_str(due_str)
    except InvalidDateFormat:
        raise
    # create task
    task = {
        "name": name,
        "type": typ,
        "desc": desc,
        "due": due_str,
        "rep": rep,
        "prio": prio,
        "done": False,
        "ctime": now_ctime_str(),
        "id": _next_id
    }
    _tasks.append(task)
    _next_id += 1
    print("Command success: " + original)
    return

def cmd_list(args: Dict[str, str], original: str):
    allowed = {"property", "val", "sort_by", "direction"}
    for k in args.keys():
        if k not in allowed:
            raise TooManyArguments()
    if "property" not in args or "val" not in args:
        raise MissingArguments()
    prop = args["property"]
    val = args["val"]
    if prop not in PROPERTIES:
        raise InvalidArgument()
    sort_by, direction = validate_sort_args(args)
    # filter case-insensitive (stringified)
    filtered = []
    for t in _tasks:
        # stringify the property
        v = str(t.get(prop, ""))
        if v.lower() == val.lower():
            filtered.append(t)
    print("Command success: " + original)
    print_header_and_tasks(filtered, sort_by, direction)
    return

def cmd_mod(args: Dict[str, str], original: str):
    allowed = {"id", "property", "new_val"}
    for k in args.keys():
        if k not in allowed:
            raise TooManyArguments()
    if "id" not in args or "property" not in args or "new_val" not in args:
        raise MissingArguments()
    try:
        idv = int(args["id"])
    except Exception:
        raise InvalidArgumentType()
    prop = args["property"]
    new_val = args["new_val"]
    if prop not in PROPERTIES:
        raise InvalidArgument()
    # find task
    task = next((t for t in _tasks if t["id"] == idv), None)
    if task is None:
        raise TaskNotFound()
    # Validate per-property
    if prop == "due":
        try:
            parse_date_str(new_val)
        except InvalidDateFormat:
            raise
        task["due"] = new_val
    elif prop == "rep":
        if new_val not in VALID_REPS:
            raise InvalidRepeat()
        task["rep"] = new_val
    elif prop == "prio":
        if new_val not in VALID_PRIOS:
            raise InvalidPriority()
        task["prio"] = new_val
    elif prop == "done":
        try:
            b = parse_bool_str(new_val)
        except InvalidDoneStatus:
            raise
        task["done"] = b
    elif prop == "id":
        # Resist changing id to keep uniqueness; spec lists id among properties but modifying id would break invariants.
        raise InvalidArgument()
    elif prop == "ctime":
        # Do not allow editing ctime
        raise InvalidArgument()
    else:
        # name, type, desc allowed, validate type for name
        if prop == "name" and new_val.isdigit():
            raise InvalidArgumentType()
        task[prop] = new_val
    print("Command success: " + original)
    return

def cmd_done(args: Dict[str, str], original: str):
    allowed = {"id"}
    for k in args.keys():
        if k not in allowed:
            raise TooManyArguments()
    if "id" not in args:
        raise MissingArguments()
    try:
        idv = int(args["id"])
    except Exception:
        raise InvalidArgumentType()
    task = next((t for t in _tasks if t["id"] == idv), None)
    if task is None:
        raise TaskNotFound()
    task["done"] = True
    print("Command success: " + original)
    return

def cmd_delete(args: Dict[str, str], original: str):
    """Delete either a single task by id (id=<int>) or all tasks matching property/val (case-insensitive).
    Errors:
    - MissingArguments: if neither id nor property+val provided
    - TooManyArguments: if unknown args present
    - InvalidArgument: invalid property name
    - InvalidArgumentType: non-integer id
    - TaskNotFound: when no matching task found to delete
    """
    allowed = {"id", "property", "val"}
    for k in args.keys():
        if k not in allowed:
            raise TooManyArguments()
    # id delete
    if "id" in args:
        # disallow combining id with property/val
        if "property" in args or "val" in args:
            raise TooManyArguments()
        try:
            idv = int(args["id"])
        except Exception:
            raise InvalidArgumentType()
        idx = next((i for i, t in enumerate(_tasks) if t["id"] == idv), None)
        if idx is None:
            raise TaskNotFound()
        # remove the task
        _tasks.pop(idx)
        print("Command success: " + original)
        return
    # batch delete by property/val
    if "property" not in args or "val" not in args:
        raise MissingArguments()
    prop = args["property"]
    val = args["val"]
    if prop not in PROPERTIES:
        raise InvalidArgument()
    # find matching tasks (case-insensitive string comparison)
    to_delete = [t for t in _tasks if str(t.get(prop, "")).lower() == val.lower()]
    if not to_delete:
        raise TaskNotFound()
    # remove them
    remaining = [t for t in _tasks if t not in to_delete]
    _tasks.clear()
    _tasks.extend(remaining)
    print("Command success: " + original)
    return

# --- Helpers for printing and sorting ---
def sort_key_func(sort_by: str):
    def keyfn(task):
        if sort_by == "name":
            return task["name"].lower()
        if sort_by == "type":
            return task["type"].lower()
        if sort_by == "desc":
            return task["desc"].lower()
        if sort_by == "due":
            if task["due"] == "NONE":
                # push NONE after real dates
                return (1, None)
            try:
                d = parse_date_str(task["due"])
                return (0, d.toordinal())
            except InvalidDateFormat:
                return (1, None)
        if sort_by == "rep":
            return task["rep"]
        if sort_by == "prio":
            return PRIORITY_ORDER.get(task["prio"], 0)
        if sort_by == "done":
            return task["done"]
        if sort_by == "ctime":
            # parse ctime like "9-10-2025 13:37:31"
            try:
                parts = task["ctime"].split(" ")
                dparts = parts[0].split("-")
                tparts = parts[1].split(":")
                dt = datetime(int(dparts[2]), int(dparts[1]), int(dparts[0]),
                              int(tparts[0]), int(tparts[1]), int(tparts[2]))
                return dt.timestamp()
            except Exception:
                return 0
        if sort_by == "id":
            return task["id"]
        return task.get(sort_by, "")
    return keyfn

def print_header_and_tasks(tasks: List[Dict[str, Any]], sort_by: str, direction: str):
    # Header as spec
    print("Name | Type | Desc | Due | Rep | Prio | Done | Ctime | Id")
    reverse = (direction == "desc")
    sorted_tasks = sorted(tasks, key=sort_key_func(sort_by), reverse=reverse)
    for t in sorted_tasks:
        due_display = t["due"] if t["due"] == "NONE" else t["due"]
        # ctime printed as stored
        print(f'{t["name"]} | {t["type"]} | {t["desc"]} | {due_display} | {t["rep"]} | {t["prio"]} | {t["done"]} | {t["ctime"]} | {t["id"]}')
        print("")  # extra blank line between tasks

# --- Top-level orchestration ---
def process_line(line: str):
    line = line.rstrip("\n")
    if not line.strip():
        return
    if len(line) > 1024:
        raise TooLongLine()
    orig = line
    # skip comment lines
    if line.strip().startswith("#"):
        return
    # command is first token (letters)
    m = re.match(r"^\s*(\w+)", line)
    if not m:
        raise InvalidArgument()
    cmd = m.group(1)
    rest = line[m.end():].strip()
    # parse args
    try:
        args = tokenize_args_segment(rest) if rest else {}
    except TooManyArguments:
        raise
    except InvalidArgument:
        raise
    # dispatch and handle TaskMgrError here so callers (including tests
    # that call `process_line` directly) see printed error messages rather
    # than uncaught exceptions.
    try:
        if cmd == "help":
            if args:
                raise TooManyArguments()
            cmd_help(args, orig)
        elif cmd == "print":
            cmd_print(args, orig)
        elif cmd == "add":
            cmd_add(args, orig)
        elif cmd == "list":
            cmd_list(args, orig)
        elif cmd == "mod":
            cmd_mod(args, orig)
        elif cmd == "done":
            cmd_done(args, orig)
        elif cmd == "delete":
            cmd_delete(args, orig)
        else:
            # unknown command
            raise InvalidArgument()
    except TaskMgrError as e:
        err_name = type(e).__name__
        print(f"Error {err_name}: {orig}")
    except Exception:
        # unexpected errors are mapped to InvalidArgument per spec
        print(f"Error InvalidArgument: {orig}")

def run_from_file(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n")
                try:
                    process_line(line)
                except TaskMgrError as e:
                    # Map exception type to error token string
                    err_name = type(e).__name__
                    print(f"Error {err_name}: {line}")
                except Exception:
                    # Unexpected errors mapped generically to InvalidArgument
                    print(f"Error InvalidArgument: {line}")
    except FileNotFoundError:
        print(f"Input file not found: {path}")
        sys.exit(2)

def main(argv):
    if len(argv) != 2:
        print("Usage: taskmgr <input-file>")
        sys.exit(2)
    run_from_file(argv[1])

if __name__ == "__main__":
    main(sys.argv)