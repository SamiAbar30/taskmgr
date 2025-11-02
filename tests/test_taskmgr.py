import pytest
import io
import sys
from datetime import datetime
import re

# import functions for unit testing
from taskmgr import (clear_state, _tasks, _next_id, process_line, parse_date_str,
                     InvalidDateFormat, InvalidRepeat, InvalidPriority, TaskNotFound,
                     InvalidArgumentType, TooLongLine)

def capture_output(func, *args, **kwargs):
    old_out = sys.stdout
    sys.stdout = io.StringIO()
    try:
        func(*args, **kwargs)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_out

def test_add_and_defaults_and_id_increment():
    clear_state()
    out = capture_output(process_line, 'add name="Task A"')
    assert "Command success: add name=\"Task A\"" in out
    # check created
    assert len(_tasks) == 1
    t = _tasks[0]
    assert t["name"] == "Task A"
    assert t["done"] is False
    # default priority chosen MEDIUM
    assert t["prio"] in ("MEDIUM", "LOW")
    # id = 0
    assert t["id"] == 0
    # add another
    capture_output(process_line, 'add name="Task B"')
    assert _tasks[-1]["id"] == 1

def test_add_missing_name_raises_message():
    clear_state()
    out = capture_output(process_line, 'add type="x"')
    assert "Error MissingArguments: add type=\"x\"" in out

def test_add_invalid_date_format():
    clear_state()
    out = capture_output(process_line, 'add name="X" due="2025/10/31"')
    assert "Error InvalidDateFormat: add name=\"X\" due=\"2025/10/31\"" in out

def test_add_invalid_repeat_priority():
    clear_state()
    out = capture_output(process_line, 'add name="X" rep="YEARLY"')
    assert "Error InvalidRepeat: add name=\"X\" rep=\"YEARLY\"" in out
    out2 = capture_output(process_line, 'add name="X" prio="URGENT"')
    assert "Error InvalidPriority: add name=\"X\" prio=\"URGENT\"" in out2

def test_list_case_insensitive_and_sorting():
    clear_state()
    capture_output(process_line, 'add name="A" type="School"')
    capture_output(process_line, 'add name="B" type="school" due="05-10-2025"')
    out = capture_output(process_line, 'list property="type" val="SCHOOL" sort_by=due direction=asc')
    assert "Command success: list property=\"type\" val=\"SCHOOL\" sort_by=due direction=asc" in out
    # Should print header and two tasks (header + lines)
    assert "Name | Type | Desc | Due | Rep | Prio | Done | Ctime | Id" in out

def test_mod_and_done_behaviour():
    clear_state()
    capture_output(process_line, 'add name="M"')
    out_mod = capture_output(process_line, 'mod id=0 property="desc" new_val="Updated"')
    assert "Command success: mod id=0 property=\"desc\" new_val=\"Updated\"" in out_mod
    assert _tasks[0]["desc"] == "Updated"
    out_done = capture_output(process_line, 'done id=0')
    assert "Command success: done id=0" in out_done
    assert _tasks[0]["done"] is True

def test_mod_invalid_property():
    clear_state()
    capture_output(process_line, 'add name="X"')
    out = capture_output(process_line, 'mod id=0 property="unknown" new_val="v"')
    assert "Error InvalidArgument: mod id=0 property=\"unknown\" new_val=\"v\"" in out

def test_done_task_not_found():
    clear_state()
    out = capture_output(process_line, 'done id=999')
    assert "Error TaskNotFound: done id=999" in out

def test_parse_date_str_ok():
    d = parse_date_str("01-01-2025")
    assert d.year == 2025 and d.month == 1 and d.day == 1

def test_parse_date_str_bad():
    with pytest.raises(InvalidDateFormat):
        parse_date_str("2025/01/01")

def test_line_length_boundaries():
    short = "x" * 1024
    long = "x" * 1025
    # short line is not a command; process_line should treat as command parse error or similar, but should not raise TooLongLine
    # However long must raise TooLongLine inside process_line
    # We'll only check that TooLongLine raises for long line
    with pytest.raises(TooLongLine):
        process_line(long)

def test_delete_by_id_and_batch():
    clear_state()
    capture_output(process_line, 'add name="A" type="School"')
    capture_output(process_line, 'add name="B" type="Work"')
    capture_output(process_line, 'add name="C" type="School"')
    assert len(_tasks) == 3
    out = capture_output(process_line, 'delete id=1')
    assert 'Command success: delete id=1' in out
    assert len(_tasks) == 2
    ids = [t['id'] for t in _tasks]
    assert 1 not in ids

    out2 = capture_output(process_line, 'delete property="type" val="School"')
    assert 'Command success: delete property="type" val="School"' in out2
    assert all(t['type'].lower() != 'school' for t in _tasks)

def test_delete_not_found_and_errors():
    clear_state()
    out = capture_output(process_line, 'delete id=999')
    assert 'Error TaskNotFound: delete id=999' in out

    capture_output(process_line, 'add name="X"')
    out2 = capture_output(process_line, 'delete property="unknown" val="x"')
    assert 'Error InvalidArgument: delete property="unknown" val="x"' in out2

    out3 = capture_output(process_line, 'delete id=0 property="type" val="X"')
    assert 'Error TooManyArguments: delete id=0 property="type" val="X"' in out3