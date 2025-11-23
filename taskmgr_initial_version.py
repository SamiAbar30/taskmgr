import sys
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional

# =============================================================================
# 1. CONFIGURATION & CONSTANTS
# =============================================================================

# Priority mapping and validation sets
PRIORITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
VALID_PRIOS = set(PRIORITY_ORDER.keys())
VALID_REPS = {"NONE", "DAILY", "WEEKLY", "MONTHLY"}
VALID_DIRECTION = {"asc", "desc"}

# Default values
DEFAULT_PRIORITY = "LOW"
DEFAULT_REP = "NONE"
DEFAULT_DUE = "NONE"

# Valid task properties
PROPERTIES = ["name", "type", "desc", "due", "rep", "prio", "done", "ctime", "id"]

# Regex for parsing "key=value" arguments, handling quotes
ARG_PAIR_RE = re.compile(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))')

# Global States
_tasks: List[Dict[str, Any]] = []
_next_id = 0


# =============================================================================
# 2. CUSTOM EXCEPTIONS
# =============================================================================

class TaskMgrError(Exception): pass
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


# =============================================================================
# 3. UTILITY FUNCTIONS
# =============================================================================

def now_ctime_str() -> str:
    """Returns current timestamp with second accuracy."""
    dt = datetime.now()
    return f"{dt.day}-{dt.month}-{dt.year} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"

def parse_date_str(s: str) -> Optional[date]:
    """Parses DD-MM-YYYY format. Returns date obj or raises error."""
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

def parse_bool_str(s: str) -> bool:
    """Parses boolean string (case-insensitive) for 'done' status."""
    s_lower = s.lower()
    if s_lower == "true": return True
    if s_lower == "false": return False
    raise InvalidDoneStatus()

def tokenize_args_segment(segment: str) -> Dict[str, str]:
    """
    Parses the argument string into a dictionary.
    Handles quoted values and detects invalid formats.
    """
    args = {}
    pos = 0
    for m in ARG_PAIR_RE.finditer(segment):
        key = m.group(1)
        # Group 2: double quotes, Group 3: single quotes, Group 4: unquoted
        val = m.group(2) or m.group(3) or m.group(4)
        args[key] = val
        pos = m.end()

    # If there is text left over that didn't match, the format is invalid
    if segment[pos:].strip():
        raise InvalidArgument()
    return args

def validate_sort_args(args: Dict[str, str]):
    """Helper to validate sorting parameters common to multiple commands."""
    sort_by = args.get("sort_by", "name")
    direction = args.get("direction", "asc")
    if direction not in VALID_DIRECTION:
        raise InvalidArgument()
    if sort_by not in PROPERTIES:
        raise InvalidArgument()
    return sort_by, direction

def sort_key_func(sort_by: str):
    """Generates the sorting key based on the property selected."""
    def keyfn(task):
        val = task.get(sort_by, "")
        
        if sort_by == "due":
            # Sort dates specially; NONE goes last (or first depending on logic)
            if task["due"] == "NONE": return (1, None)
            try:
                return (0, parse_date_str(task["due"]).toordinal())
            except InvalidDateFormat: return (1, None)
            
        elif sort_by == "prio":
            return PRIORITY_ORDER.get(task["prio"], 0)
        
        elif sort_by == "ctime":
            try:
                # Custom parsing for the specific ctime format used
                parts = task["ctime"].split(" ")
                dparts = parts[0].split("-")
                tparts = parts[1].split(":")
                dt = datetime(int(dparts[2]), int(dparts[1]), int(dparts[0]),
                              int(tparts[0]), int(tparts[1]), int(tparts[2]))
                return dt.timestamp()
            except Exception: return 0
            
        return val.lower() if isinstance(val, str) else val
    return keyfn

def print_header_and_tasks(tasks: List[Dict[str, Any]], sort_by: str, direction: str):
    """Formats and prints the task list."""
    print("Name | Type | Desc | Due | Rep | Prio | Done | Ctime | Id")
    reverse = (direction == "desc")
    sorted_tasks = sorted(tasks, key=sort_key_func(sort_by), reverse=reverse)
    
    for t in sorted_tasks:
        due_display = t["due"] if t["due"] != "NONE" else "NONE"
        print(f'{t["name"]} | {t["type"]} | {t["desc"]} | {due_display} | '
              f'{t["rep"]} | {t["prio"]} | {t["done"]} | {t["ctime"]} | {t["id"]}')
        print("")


# =============================================================================
# 4. COMMAND HANDLERS
# =============================================================================

def cmd_help(args: Dict[str, str], original: str):
    """Displays usage information."""
    print("Command success: " + original)
    print("help")
    print("print [sort_by=<prop>] [direction=<asc|desc>]")
    print("add name=<name> [type=<type>] [desc=<desc>] [due=<DD-MM-YYYY>] "
          "[rep=<NONE|DAILY|WEEKLY|MONTHLY>] [prio=<LOW|MEDIUM|HIGH>]")
    print("list property=<prop> val=<value> [sort_by=<prop>] [direction=<asc|desc>]")
    print("mod id=<id> property=<prop> new_val=<value>")
    print("done id=<id>")

def cmd_print(args: Dict[str, str], original: str):
    """Prints all tasks with optional sorting."""
    allowed = {"sort_by", "direction"}
    if any(k not in allowed for k in args):
        raise TooManyArguments()
        
    sort_by, direction = validate_sort_args(args)
    print("Command success: " + original)
    print_header_and_tasks(_tasks, sort_by, direction)

def cmd_add(args: Dict[str, str], original: str):
    """Adds a new task."""
    global _next_id
    allowed = {"name", "type", "desc", "due", "rep", "prio"}
    
    if any(k not in allowed for k in args):
        raise TooManyArguments()
    if "name" not in args:
        raise MissingArguments()
        
    name = args["name"]
    if name.isdigit(): # Name cannot be a number
        raise InvalidArgumentType()
        
    # Extract and validate optional fields
    typ = args.get("type", "NONE")
    desc = args.get("desc", "")
    due_str = args.get("due", DEFAULT_DUE)
    rep = args.get("rep", DEFAULT_REP)
    prio = args.get("prio", DEFAULT_PRIORITY)

    if rep not in VALID_REPS: raise InvalidRepeat()
    if prio not in VALID_PRIOS: raise InvalidPriority()
    if due_str != "NONE": parse_date_str(due_str) # Validate date format

    task = {
        "name": name, "type": typ, "desc": desc, "due": due_str,
        "rep": rep, "prio": prio, "done": False,
        "ctime": now_ctime_str(), "id": _next_id
    }
    _tasks.append(task)
    _next_id += 1
    print("Command success: " + original)

def cmd_list(args: Dict[str, str], original: str):
    """Lists tasks matching a specific property value."""
    allowed = {"property", "val", "sort_by", "direction"}
    if any(k not in allowed for k in args):
        raise TooManyArguments()
    if "property" not in args or "val" not in args:
        raise MissingArguments()
        
    prop = args["property"]
    val = args["val"]
    if prop not in PROPERTIES:
        raise InvalidArgument()
        
    sort_by, direction = validate_sort_args(args)
    
    # Filter tasks (case-insensitive match)
    filtered = [t for t in _tasks if str(t.get(prop, "")).lower() == val.lower()]
    
    print("Command success: " + original)
    print_header_and_tasks(filtered, sort_by, direction)

def cmd_mod(args: Dict[str, str], original: str):
    """Modifies a specific property of a task by ID."""
    allowed = {"id", "property", "new_val"}
    if any(k not in allowed for k in args):
        raise TooManyArguments()
    if not all(k in args for k in ["id", "property", "new_val"]):
        raise MissingArguments()
        
    try:
        idv = int(args["id"])
    except Exception:
        raise InvalidArgumentType()
        
    prop = args["property"]
    new_val = args["new_val"]
    
    if prop not in PROPERTIES:
        raise InvalidArgument()
        
    # Find task
    task = next((t for t in _tasks if t["id"] == idv), None)
    if task is None:
        raise TaskNotFound()
        
    # Property-specific validation and assignment
    if prop == "due":
        parse_date_str(new_val) # Check format
        task["due"] = new_val
    elif prop == "rep":
        if new_val not in VALID_REPS: raise InvalidRepeat()
        task["rep"] = new_val
    elif prop == "prio":
        if new_val not in VALID_PRIOS: raise InvalidPriority()
        task["prio"] = new_val
    elif prop == "done":
        task["done"] = parse_bool_str(new_val)
    elif prop in ["id", "ctime"]:
        # ID and Ctime are immutable
        raise InvalidArgument()
    else:
        if prop == "name" and new_val.isdigit():
            raise InvalidArgumentType()
        task[prop] = new_val
        
    print("Command success: " + original)

def cmd_done(args: Dict[str, str], original: str):
    """Marks a task as done by ID."""
    allowed = {"id"}
    if any(k not in allowed for k in args):
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


# =============================================================================
# 5. CORE EXECUTION LOGIC
# =============================================================================

def process_line(line: str):
    """
    Processes a single line of input.
    1. Checks length limits.
    2. Parses command and arguments.
    3. Dispatches to specific command handler.
    4. Catches and prints errors.
    """
    line = line.rstrip("\n")
    if not line.strip() or line.strip().startswith("#"):
        return # Skip empty lines or comments

    if len(line) > 1024:
        raise TooLongLine()
        
    orig = line
    m = re.match(r"^\s*(\w+)", line)
    if not m:
        raise InvalidArgument()
        
    cmd = m.group(1)
    rest = line[m.end():].strip()
    
    try:
        args = tokenize_args_segment(rest) if rest else {}
    except (TooManyArguments, InvalidArgument):
        # Re-raise parsing errors to be caught by the main error block
        raise

    try:
        if cmd == "help":
            if args: raise TooManyArguments()
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
        else:
            raise InvalidArgument()
            
    except TaskMgrError as e:
        print(f"Error {type(e).__name__}: {orig}")
    except Exception:
        # Fallback for unexpected errors
        print(f"Error InvalidArgument: {orig}")

def run_from_file(path: str):
    """Reads the input file line by line and processes commands."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n")
                try:
                    process_line(line)
                except TaskMgrError as e:
                    print(f"Error {type(e).__name__}: {line}")
                except Exception:
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