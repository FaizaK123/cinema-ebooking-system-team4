"""Sends account emails (confirmation, password reset, profile-change notices).

With SMTP settings in backend/.env, emails are really sent (e.g. through Gmail).
Without them, each email is saved as a text file in backend/instance/outbox/ and
printed to the terminal, so the app still works on a teammate's machine.
"""
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

import config


class EmailService:
    @staticmethod
    def send(to_address, subject, body):
        """Returns True if the email was delivered (or saved to the dev outbox)."""
        if not config.SMTP_HOST:
            return EmailService._save_to_outbox(to_address, subject, body)

        message = EmailMessage()
        message["From"] = f"Cinema E-Booking <{config.MAIL_FROM}>"
        message["To"] = to_address
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if config.SMTP_USERNAME:
                    smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                smtp.send_message(message)
            return True
        except (smtplib.SMTPException, OSError) as error:
            print(f"[email] Could not send '{subject}' to {to_address}: {error}")
            return False

    @staticmethod
    def check_connection():
        """Logs in to the SMTP server once at startup and prints a clear warning if it fails."""
        if not config.SMTP_HOST:
            print("[email] SMTP not configured: emails will be saved to backend/instance/outbox/.")
            return
        try:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if config.SMTP_USERNAME:
                    smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            print(f"[email] SMTP login OK ({config.SMTP_USERNAME}).")
        except (smtplib.SMTPException, OSError) as error:
            print(f"[email] WARNING: SMTP login failed, so no emails will be sent: {error}\n"
                  "        Check SMTP_PASSWORD in backend/.env (Gmail needs 2-Step Verification on and a valid app password).")

    @staticmethod
    def _save_to_outbox(to_address, subject, body):
        config.OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        path = config.OUTBOX_DIR / f"{stamp}.txt"
        path.write_text(f"To: {to_address}\nSubject: {subject}\n\n{body}\n", encoding="utf-8")
        print(f"[email] SMTP not configured. Saved '{subject}' for {to_address} to {path}")
        return True

    # ---- Message templates ----

    @staticmethod
    def send_verification(user_first_name, to_address, link):
        body = (
            f"Hi {user_first_name},\n\n"
            "Thanks for signing up for Cinema E-Booking! Confirm your email address to activate your account:\n\n"
            f"{link}\n\n"
            f"This link expires in {config.VERIFY_TOKEN_HOURS} hours. "
            "If you didn't create an account, you can ignore this email.\n"
        )
        return EmailService.send(to_address, "Confirm your Cinema E-Booking account", body)

    @staticmethod
    def send_password_reset(user_first_name, to_address, link):
        body = (
            f"Hi {user_first_name},\n\n"
            "We received a request to reset your Cinema E-Booking password. Choose a new password here:\n\n"
            f"{link}\n\n"
            f"This link expires in {config.RESET_TOKEN_MINUTES} minutes and can only be used once. "
            "If you didn't ask to reset your password, you can ignore this email; your password won't change.\n"
        )
        return EmailService.send(to_address, "Reset your Cinema E-Booking password", body)

    @staticmethod
    def send_account_change(user_first_name, to_address, changes):
        """Security notice sent whenever profile, address, card or password details change."""
        change_lines = "\n".join(f"  - {change}" for change in changes)
        body = (
            f"Hi {user_first_name},\n\n"
            "The following changes were made to your Cinema E-Booking account:\n\n"
            f"{change_lines}\n\n"
            f"Time: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n\n"
            "If you made these changes, no action is needed. If you didn't, reset your password "
            "right away using 'Forgot Password?' on the login page.\n"
        )
        return EmailService.send(to_address, "Your Cinema E-Booking account was updated", body)
