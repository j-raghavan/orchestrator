import base64
import os

import apprise
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    Disposition,
    FileContent,
    FileName,
    FileType,
    Mail,
)

from . import register_notifier
from .common import EmailNotifier


class CustomNotifySendGrid(apprise.NotifyBase):
    # Subclass of NotifySendGrid to support attachments
    def __init__(self, **kwargs):
        super(CustomNotifySendGrid, self).__init__(**kwargs)
        self.api_key = kwargs.get("api_key")
        self.from_email = kwargs.get("from_email")
        self.to_email = kwargs.get("to_email")
        self.sg = SendGridAPIClient(self.api_key)

    def notify(self, body, title="", attach_paths=None):
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=self.to_email,
                subject=title,
                html_content=body,
            )

            if attach_paths:
                for attachment_path in attach_paths:
                    with open(attachment_path, "rb") as f:
                        file_data = f.read()
                        encoded_file = base64.b64encode(file_data).decode()

                    attachment = Attachment(
                        FileContent(encoded_file),
                        FileName(os.path.basename(attachment_path)),
                        FileType("application/octet-stream"),
                        Disposition("attachment"),
                    )
                    message.add_attachment(attachment)

            response = self.sg.send(message)

            if response.status_code == 202:
                print("Notification sent successfully")
                return True
            else:
                print(f"Failed to send notification: {response.status_code}")
                return False

        except Exception as e:
            print(f"EXCEPTION: An error occurred while sending the notification {e}")
            return False


@register_notifier("SendGridNotifier")
class SendGridNotifier(EmailNotifier):
    """
    A class representing a SendGrid notifier for sending email notifications.

    Args:
        sender (str): The email address of the sender.
        recipients (list): A list of email addresses of the recipients.
        subject (str): The subject of the email.
        body (str): The body of the email.
        attachments (list, optional): A list of file paths for attachments.

    Raises:
        AssertionError: If the SENDGRID_API_KEY environment variable is not set.

    Attributes:
        body (str): The body of the email.
        subject (str): The subject of the email.
        apobj (apprise.Apprise): An instance of the Apprise class for sending notifications.

    """

    def __init__(self, sender, recipients, subject, body, attachments=None):
        super().__init__(sender, recipients, subject, body, attachments)
        assert os.environ.get("SENDGRID_API_KEY"), "SENDGRID_API_KEY is not set"
        self.logger.debug(
            f"Initialized SendGrid Notifier with sender: {sender}, "
            f"recipients: {recipients}, subject: {subject}"
        )
        self.body = body
        self.subject = subject

        self.apobj = CustomNotifySendGrid(
            api_key=os.environ.get("SENDGRID_API_KEY"),
            from_email=sender,
            to_email=", ".join(recipients),
        )

        self.logger.debug("Apprise object initialized")

    def send(self, attachments: list = None):
        """
        Sends the email notification using SendGrid.

        Raises:
            Exception: If the notification fails to send.

        """
        success = self.apobj.notify(
            body=self.body, title=self.subject, attach_paths=attachments
        )
        if not success:
            raise Exception("Failed to send notification")

        self.logger.info("Sending email using SendGrid")
