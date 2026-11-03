import smtplib
from email.message import EmailMessage

from ..config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS


def send_mail(to: str, subject: str, body: str):
    #메일 설정이 없는 PC는 서버 로그에 출력한다 (개발용)
    if not SMTP_USER:
        print(f"[메일 대신 로그] 받는 사람: {to}\n제목: {subject}\n{body}", flush=True)
        return

    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)