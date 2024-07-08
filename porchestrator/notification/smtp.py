import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from . import register_notifier
from .common import EmailNotifier


@register_notifier("SMTPNotifier")
class SMTPNotifier(EmailNotifier):
    """
    A class representing an SMTP notifier.

    This class inherits from the `EmailNotifier` class and provides functionality
    to send email notifications using the SMTP protocol.

    Args:
        smtp_server (str): The SMTP server address.
        port (int, optional): The port number to connect to the SMTP server. Defaults to 587.
        username (str): The username for authentication.
        password (str, optional): The password for authentication. If not provided, it will be fetched from the environment variable `SMTP_PASSWORD`.
        from_email (str): The email address of the sender.
        to_email (str): The email address of the recipient.
        subject (str): The subject of the email.
        body (str): The body content of the email.
        attachment_path (str, optional): The path to the attachment file.

    Methods:
        _create_attachment(attachment_path): Creates an attachment object for the given attachment path.
        send(body, attachment_path): Sends the email with the provided body and attachment (if any).

    """

    def __init__(self, **kwargs):
        super(SMTPNotifier, self).__init__(**kwargs)
        self.smtp_server = kwargs.get("smtp_server")
        self.port = kwargs.get("port", 587)
        self.username = kwargs.get("username")
        self.password = kwargs.get("password", os.environ.get("SMTP_PASSWORD"))
        self.from_email = kwargs.get("from_email")
        self.to_email = kwargs.get("to_email")
        self.subject = kwargs.get("subject")
        self.body = kwargs.get("body")
        self.attachment_path = kwargs.get("attachment_path")

    def _create_attachment(self, attachment_path):
        """
        Creates an attachment object for the given attachment path.

        Args:
            attachment_path (str): The path to the attachment file.

        Returns:
            attachment (MIMEBase): The attachment object.

        """
        attachment = MIMEBase("application", "octet-stream")
        with open(attachment_path, "rb") as file:
            attachment.set_payload(file.read())
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f"attachment; filename={os.path.basename(attachment_path)}",
        )
        return attachment

    def send(self, body, attachment_path=None):
        """
        Sends the email with the provided body and attachment (if any).

        Args:
            body (str): The body content of the email.
            attachment_path (str, optional): The path to the attachment file.

        """
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = self.to_email
            msg["Subject"] = self.subject
            msg.attach(MIMEText(body, "plain"))

            if attachment_path:
                attachment = self._create_attachment(attachment_path)
                msg.attach(attachment)

            server = smtplib.SMTP(host=self.smtp_server, port=self.port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.from_email, self.to_email, text)
            server.quit()

            self.logger.info(f"Email sent via SMTP to {self.to_email}")
            return True

        except smtplib.SMTPException as e:
            self.logger.critical(f"SMTPException occurred: {str(e)}")
            return False
        except Exception as e:
            self.logger.critical(f"An unexpected error occurred: {str(e)}")
            return False
