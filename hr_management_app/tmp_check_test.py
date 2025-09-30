from database import record_check_in, record_check_out, has_open_session, has_checked_out_today

TEST_ID = 99999
print('initial open:', has_open_session(TEST_ID))
ci = record_check_in(TEST_ID)
print('checked in at', ci)
print('open after in:', has_open_session(TEST_ID))
out = record_check_out(TEST_ID)
print('checked out at', out)
print('checked out today?', has_checked_out_today(TEST_ID))
out2 = record_check_out(TEST_ID)
print('second checkout attempt result:', out2)
