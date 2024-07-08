import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from . import register_notifier
from .common import EmailNotifier


@register_notifier("SESNotifier")
class SESNotifier(EmailNotifier):
    """
    A class for sending email notifications using the Amazon SES service.

    Args:
        aws_access_key_id (str): The AWS access key ID.
        aws_secret_access_key (str): The AWS secret access key.
        region_name (str): The AWS region name.
        from_email (str): The sender's email address.
        to_email (str): The recipient's email address.
        subject (str): The subject of the email.
        body (str): The body of the email.

    Attributes:
        aws_access_key_id (str): The AWS access key ID.
        aws_secret_access_key (str): The AWS secret access key.
        region_name (str): The AWS region name.
        from_email (str): The sender's email address.
        to_email (str): The recipient's email address.
        subject (str): The subject of the email.
        body (str): The body of the email.
    """

    def __init__(self, **kwargs):
        super(SESNotifier, self).__init__(**kwargs)
        self.aws_access_key_id = kwargs.get(
            "aws_access_key_id", os.environ.get("AWS_ACCESS_KEY_ID")
        )
        self.aws_secret_access_key = kwargs.get(
            "aws_secret_access_key", os.environ.get("AWS_SECRET_ACCESS_KEY")
        )
        self.region_name = kwargs.get("region_name", "us-west-2")
        self.from_email = kwargs.get("from_email")
        self.to_email = kwargs.get("to_email")
        self.subject = kwargs.get("subject")
        self.body = kwargs.get("body")

    def _create_attachment(self, attachment_path):
        """
        Create an email attachment from a file.

        Args:
            attachment_path (str): The path to the file to be attached.

        Returns:
            MIMEBase: The MIMEBase object representing the attachment.
        """
        part = MIMEBase("application", "octet-stream")
        with open(attachment_path, "rb") as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {os.path.basename(attachment_path)}",
        )
        return part

    def send(self, body, attachment_path: list = None):
        """
        Send an email notification.

        Args:
            body (str): The body of the email.
            title (str, optional): The title of the email. Defaults to None.
            attachment_path (str, optional): The path to the file to be attached. Defaults to None.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        try:
            client = boto3.client(
                "ses",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region_name,
            )
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = self.to_email
            msg["Subject"] = self.subject
            msg.attach(MIMEText(body, "plain"))

            if attachment_path:
                part = self._create_attachment(attachment_path)
                msg.attach(part)

            response = client.send_raw_email(
                Source=self.from_email,
                Destinations=[self.to_email],
                RawMessage={"Data": msg.as_string()},
            )
            if not response:
                self.logger.error("Failed to send email notification")
                return False

            # Check for response status code and return True if successful
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                self.logger.debug("Notification sent successfully")

            return True
        except (BotoCoreError, ClientError, NoCredentialsError) as e:
            self.logger.critical(f"Error sending email notification: {str(e)}")
            return False
