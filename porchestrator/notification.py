import base64
import os
import smtplib
from collections import defaultdict
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
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


class SMTPClient:
    def __init__(self, service):
        self.service = service
        self.config = defaultdict(str)

    @property
    def aws_access_key_id(self):
        return self.config["aws_access_key_id"]

    @aws_access_key_id.setter
    def aws_access_key_id(self, value):
        self.config["aws_access_key_id"] = value

    @property
    def aws_secret_access_key(self):
        return self.config["aws_secret_access_key"]

    @aws_secret_access_key.setter
    def aws_secret_access_key(self, value):
        self.config["aws_secret_access_key"] = value

    @property
    def region_name(self):
        return self.config["region_name"]

    @region_name.setter
    def region_name(self, value):
        self.config["region_name"] = value

    @property
    def username(self):
        return self.config["username"]

    @username.setter
    def username(self, value):
        self.config["username"] = value

    @property
    def password(self):
        return self.config["password"]

    @password.setter
    def password(self, value):
        self.config["password"] = value

    @property
    def sendgrid_api_key(self):
        return self.config["sendgrid_api_key"]

    @sendgrid_api_key.setter
    def sendgrid_api_key(self, value):
        self.config["sendgrid_api_key"] = value

    @property
    def from_email(self):
        return self.config["from_email"]

    @from_email.setter
    def from_email(self, value):
        self.config["from_email"] = value

    @property
    def sendgrid_api_key(self):
        return self.config["sendgrid_api_key"]

    @sendgrid_api_key.setter
    def sendgrid_api_key(self, value):
        self.config["sendgrid_api_key"] = value

    def send_email(self, to_email, subject, body, attachment_path=None):
        retval = False
        try:
            if self.service == "aws_ses":
                self._send_via_aws_ses(to_email, subject, body, attachment_path)
                retval = True
            elif self.service == "sendgrid":
                self._send_via_sendgrid(to_email, subject, body, attachment_path)
                retval = True
            elif self.service == "gmail":
                self._send_via_gmail(to_email, subject, body, attachment_path)
                retval = True
            else:
                logger.error(f"Unsupported email service: {self.service}")
        except Exception as e:
            logger.error(f"Failed to send email via {self.service}: {e}")

        return retval

    def _send_via_aws_ses(self, to_email, subject, body, attachment_path=None):
        client = boto3.client(
            "ses",
            aws_access_key_id=self.config["aws_access_key_id"],
            aws_secret_access_key=self.config["aws_secret_access_key"],
            region_name=self.config["region_name"],
        )
        msg = MIMEMultipart()
        msg["From"] = self.config["from_email"]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        if attachment_path:
            part = self._create_attachment(attachment_path)
            msg.attach(part)

        response = client.send_raw_email(
            Source=self.config["from_email"],
            Destinations=[to_email],
            RawMessage={"Data": msg.as_string()},
        )
        logger.info(f"Email sent via AWS SES: {response}")

    def _send_via_sendgrid(self, to_email, subject, body, attachment_path=None):
        message = Mail(
            from_email=self.config["from_email"],
            to_emails=to_email,
            subject=subject,
            plain_text_content=body,
        )

        if attachment_path:
            with open(attachment_path, "rb") as f:
                data = f.read()
                encoded = base64.b64encode(data).decode()
                attachment = Attachment(
                    FileContent(encoded),
                    FileName(os.path.basename(attachment_path)),
                    FileType("application/gzip"),
                    Disposition("attachment"),
                )
                message.attachment = attachment

        sg = SendGridAPIClient(self.config["sendgrid_api_key"])
        response = sg.send(message)
        if response.status_code >= 300:
            logger.error(
                f"Failed to send email via SendGrid: "
                f"{response.status_code}, {response.body}"
            )
            raise Exception(
                f"Failed to send email via SendGrid: "
                f"{response.status_code}, {response.body}"
            )
        logger.info(f"Email sent via SendGrid: {response.status_code}")

    def _send_via_gmail(self, to_email, subject, body, attachment_path=None):
        msg = MIMEMultipart()
        msg["From"] = self.config["from_email"]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        if attachment_path:
            part = self._create_attachment(attachment_path)
            msg.attach(part)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(self.config["from_email"], self.config["password"])
        text = msg.as_string()
        server.sendmail(self.config["from_email"], to_email, text)
        server.quit()
        logger.info(f"Email sent via Gmail to {to_email}")

    def _create_attachment(self, attachment_path):
        part = MIMEBase("application", "octet-stream")
        with open(attachment_path, "rb") as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {os.path.basename(attachment_path)}",
        )
        return part


if __name__ == "__main__":
    # For Gmail
    config = {
        "aws_access_key_id": "",
        "aws_secret_access_key": "",
        "region_name": "us-west-2",
        "sendgrid_api_key": "",
        "from_email": "",
        "password": "",
    }
    # client = SMTPClient("gmail")
    # client = SMTPClient("sendgrid")
    # client = SMTPClient("aws_ses")
    # client.from_email = config.get("from_email")
    # client.password = config.get("password")
    # client.aws_access_key_id = config.get("aws_access_key_id")
    # client.aws_secret_access_key = config.get("aws_secret_access_key")
    # client.region_name = config.get("region_name")
    # client.sendgrid_api_key = config.get("sendgrid_api_key")

    # client.send_email(
    #     "jayasimha@unskript.com",
    #     "Prefect Orchestrator Test",
    #     "Test Body",
    #     "../test_data/document.tar.bz2",
    # )
