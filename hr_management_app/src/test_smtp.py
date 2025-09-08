import sys
import smtplib
from email_config import SMTP_SERVER, SMTP_PORT, SMTP_USE_SSL, SMTP_USER, SMTP_PASSWORD

def test_smtp():
    try:
        if SMTP_USE_SSL:
            s = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
        else:
            s = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            s.ehlo(); s.starttls(); s.ehlo()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASSWORD)
        s.quit()
        print("SMTP login OK")
        return 0
    except Exception as e:
        print("SMTP test failed:", type(e).__name__, e)
        return 2

if __name__ == "__main__":
    sys.exit(test_smtp())