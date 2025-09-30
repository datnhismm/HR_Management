"""
Non-visual GUI smoke simulation: exercises check-in/check-out flow using database helpers
and prints the messages the GUI would display plus attendance DB rows for inspection.
"""
from hr_management_app.src.database.database import (
    _conn,
    has_open_session,
    has_checked_out_today,
    record_check_in,
    record_check_out,
)

TEST_ID = 424242

def dump_attendance(eid):
    with _conn() as conn:
        c = conn.cursor()
        c.execute("SELECT id, employee_id, check_in, check_out FROM attendance WHERE employee_id = ? ORDER BY id", (eid,))
        rows = c.fetchall()
    print(f"Attendance rows for employee {eid}:")
    if not rows:
        print("  <none>")
    for r in rows:
        print(f"  id={r[0]} check_in={r[2]} check_out={r[3]}")

print('--- Start GUI smoke simulation (non-visual) ---')
print('Initial state:')
print('  has_open_session=', has_open_session(TEST_ID))
print('  has_checked_out_today=', has_checked_out_today(TEST_ID))

dump_attendance(TEST_ID)

print('\nSimulate user clicking Check In')
ci = record_check_in(TEST_ID)
print('  record_check_in ->', ci)
print('  has_open_session=', has_open_session(TEST_ID))
print('  has_checked_out_today=', has_checked_out_today(TEST_ID))
dump_attendance(TEST_ID)

print('\nSimulate user clicking Check Out')
out = record_check_out(TEST_ID)
print('  record_check_out ->', out)
print('  has_open_session=', has_open_session(TEST_ID))
print('  has_checked_out_today=', has_checked_out_today(TEST_ID))
dump_attendance(TEST_ID)

print('\nSimulate user attempting second Check Out (should be prevented)')
out2 = record_check_out(TEST_ID)
print('  second record_check_out ->', out2)
print('  has_open_session=', has_open_session(TEST_ID))
print('  has_checked_out_today=', has_checked_out_today(TEST_ID))
dump_attendance(TEST_ID)

print('--- End simulation ---')
