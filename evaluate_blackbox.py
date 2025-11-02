import csv
import io
import sys
from contextlib import redirect_stdout

import taskmgr

CSV_IN = 'blackbox_tests.csv'
OUT = 'blackbox_summary.csv'

def detect_expected_type(expected_text: str):
    if not expected_text:
        return 'unknown'
    # look for explicit Error TYPE
    import re
    m = re.search(r'Error\s+(\w+)', expected_text)
    if m:
        return m.group(1)
    if 'Command success' in expected_text or 'Task created' in expected_text or 'printed' in expected_text.lower():
        return 'success'
    return 'unknown'

def run():
    rows = []
    with open(CSV_IN, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    # run all commands sequentially, capturing output per command
    results = []
    # ensure fresh state
    taskmgr.clear_state()

    for r in rows:
        cid = r.get('ID','')
        cmd = (r.get('Command') or '').strip()
        expected_raw = (r.get('Expected') or '').strip()
        if not cmd:
            results.append((cid, cmd, expected_raw, '', 'SKIP'))
            continue
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                taskmgr.process_line(cmd)
            except Exception:
                # process_line should print errors; if exceptions escape, catch them
                import traceback
                print('EXCEPTION:', traceback.format_exc())
        out = buf.getvalue().strip()
        expected_type = detect_expected_type(expected_raw)
        passed = False
        if expected_type == 'success':
            if out.startswith('Command success:'):
                passed = True
        elif expected_type == 'unknown':
            # try to be lenient: if expected_raw text appears in output
            passed = expected_raw and expected_raw in out
        else:
            # expected an error type
            if f'Error {expected_type}' in out:
                passed = True

        results.append((cid, cmd, expected_raw, out.replace('\n', '\\n'), 'PASS' if passed else 'FAIL'))

    # write summary
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID','Command','Expected','Actual','Result'])
        for row in results:
            writer.writerow(row)

    print(f'Wrote summary to {OUT}')

if __name__ == '__main__':
    run()
