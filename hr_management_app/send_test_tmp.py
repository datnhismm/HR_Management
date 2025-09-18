import os
import smtplib
import sys
import uuid
from email.message import EmailMessage

# Adjust recipient if needed
to = 'truongphatdat2002ct@gmail.com'
code = 'TRACK-' + str(uuid.uuid4())[:8]
msg = EmailMessage()
msg['Subject'] = f'HR Management verification resend {code}'
msg['From'] = os.environ.get('FROM_EMAIL', os.environ.get('SMTP_USER'))
msg['To'] = to
msg.set_content('This is a resend test. Code: ' + code)

try:
    SMTP_USE_SSL = os.environ.get('SMTP_USE_SSL', 'False').lower() in ('1', 'true', 'yes')
    server = os.environ['SMTP_SERVER']
    port = int(os.environ.get('SMTP_PORT', '465'))
    if SMTP_USE_SSL:
        smtp = smtplib.SMTP_SSL(server, port, timeout=30)
    else:
        smtp = smtplib.SMTP(server, port, timeout=30)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
    smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
    res = smtp.sendmail(msg['From'], [to], msg.as_string())
    # try NOOP to get server response
    try:
        noop = smtp.noop()
    except Exception as e:
        noop = ('noop-failed', str(e))
    try:
        smtp.quit()
    except Exception:
        pass
    print('sendmail_return:', res)
    print('noop_result:', noop)
    print('tracking_code:', code)
except Exception as e:
    print('exception', type(e).__name__, e)
    sys.exit(1)
