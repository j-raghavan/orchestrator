import smtplib
import boto3
import base64
import os

from collections import defaultdict
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from email.mime.text import MIMEText
from typing import Any, Dict, List
from loguru import logger
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    Disposition,
    FileContent,
    FileName,
    FileType,
    Mail,
)

from prefect import flow, task, get_run_logger
from prefect.blocks.core import Block
from prefect.blocks.notifications import NotificationBlock
from prefect.client import get_client
from prefect.utilities.asyncutils import sync_compatible
from prefect.blocks.notifications import NotificationBlockType
from pydantic import SecretStr
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# --- Define Notification Block Types ---
class AWSSESNotificationBlockType(NotificationBlockType):
    """
    Notification block type for AWS SES.
    """
    _block_type_name = "AWS SES"
    _logo_url = "https://docs.prefect.io/img/logos/aws_logo.png"


class SendGridNotificationBlockType(NotificationBlockType):
    """
    Notification block type for SendGrid.
    """

    _block_type_name = "SendGrid"
    _logo_url = "https://docs.prefect.io/img/logos/sendgrid.png"


class SMTPNotificationBlockType(NotificationBlockType):
    """
    Notification block type for SMTP.
    """

    _block_type_name = "SMTP"
    _logo_url = "https://docs.prefect.io/img/logos/prefect-logo.png"


# --- Define a Base Notification Block (optional but recommended) ---
class BaseNotificationBlock(NotificationBlock):
    """
    Base class for notification blocks, providing common notification logic.
    """

    @sync_compatible
    async def notify(self, subject: str, body: str, recipients: List[str]):
        raise NotImplementedError()  # Subclasses must implement this


# --- AWS SES Notification Block ---
class AWS_SES_NotificationBlock(BaseNotificationBlock):
    """
    Sends email notifications using AWS SES.
    """

    _block_type_name = "AWS SES"
    _logo_url = "https://docs.prefect.io/img/logos/aws_logo.png"

    access_key_id: SecretStr
    secret_access_key: SecretStr
    region_name: str
    sender_email: str

    @sync_compatible
    async def notify(self, subject: str, body: str, recipients: List[str]):
        client = boto3.client(
            "ses",
            aws_access_key_id=self.access_key_id.get_secret_value(),
            aws_secret_access_key=self.secret_access_key.get_secret_value(),
            region_name=self.region_name,
        )
        response = client.send_email(
            Source=self.sender_email,
            Destination={"ToAddresses": recipients},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            },
        )


# --- SendGrid Notification Block ---
class SendGridNotificationBlock(BaseNotificationBlock):
    """
    Sends email notifications using SendGrid.
    """

    _block_type_name = "SendGrid"
    _logo_url = "https://docs.prefect.io/img/logos/sendgrid.png"

    api_key: SecretStr
    sender_email: str

    @sync_compatible
    async def notify(self, subject: str, body: str, recipients: List[str]):
        message = Mail(
            from_email=self.sender_email,
            to_emails=recipients,
            subject=subject,
            plain_text_content=body,
        )
        sg = SendGridAPIClient(self.api_key.get_secret_value())
        sg.send(message)


# --- SMTP Notification Block ---
class SMTPNotificationBlock(BaseNotificationBlock):
    """
    Sends email notifications using a generic SMTP server.
    """

    _block_type_name = "SMTP"
    _logo_url = "https://docs.prefect.io/img/logos/prefect-logo.png"

    smtp_server: str
    smtp_port: int
    sender_email: str
    sender_password: SecretStr

    @sync_compatible
    async def notify(self, subject: str, body: str, recipients: List[str]):
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(
                self.sender_email, self.sender_password.get_secret_value()
            )
            message = MIMEText(body)
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = ", ".join(recipients)
            server.sendmail(self.sender_email, recipients, message.as_string())


# --- Example Flow ---
@flow(name="Multi-Service Email Flow")
async def email_flow(recipients: List[str], use_aws: bool = False, use_sendgrid: bool = False):
    logger = get_run_logger()
    # Get the Prefect client
    prefect_client = await get_client()

    # Retrieve notification block names from flow parameters (or however you manage block selection)
    aws_ses_block_name = "aws-ses-block"  
    sendgrid_block_name = "sendgrid-block"  
    smtp_block_name = "smtp-block"

    # Load notification blocks from Prefect
    aws_ses_block = await prefect_client.read_block_by_name(aws_ses_block_name)
    sendgrid_block = await prefect_client.read_block_by_name(sendgrid_block_name)
    smtp_block = await prefect_client.read_block_by_name(smtp_block_name)

    subject = "Important Notification from Prefect"
    body = "Your flow has completed successfully!"

    try:
        if use_aws:
            await aws_ses_block.notify(subject, body, recipients)
            logger.info("Email notification sent successfully using AWS SES!")
        elif use_sendgrid:
            await sendgrid_block.notify(subject, body, recipients)
            logger.info("Email notification sent successfully using SendGrid!")
        else:
            await smtp_block.notify(subject, body, recipients)
            logger.info("Email notification sent successfully using SMTP!")
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")

if __name__ == "__main__":
    email_flow(
        recipients=["recipient1@example.com", "recipient2@example.com"], use_aws=True
    )