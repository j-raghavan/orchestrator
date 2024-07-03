import unittest
from unittest.mock import MagicMock, patch

from orchestrator.notification import SMTPClient


class TestSMTPClient(unittest.TestCase):

    def setUp(self):
        self.config = {
            "aws_access_key_id": "fake_aws_access_key_id",
            "aws_secret_access_key": "fake_aws_secret_access_key",
            "region_name": "us-east-1",
            "sendgrid_api_key": "fake_sendgrid_api_key",
            "from_email": "test@example.com",
            "password": "fake_password",
        }

    @patch("orchestrator.notification.boto3.client")
    def test_send_via_aws_ses(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        smtp_client = SMTPClient("aws_ses")
        smtp_client.aws_access_key_id = self.config["aws_access_key_id"]
        smtp_client.aws_secret_access_key = self.config["aws_secret_access_key"]
        smtp_client.region_name = self.config["region_name"]

        smtp_client.send_email(
            "recipient@example.com",
            "Test Subject",
            "Test Body",
            "../../test_data/document.tar.bz2",
        )

        mock_client.send_raw_email.assert_called_once()
        self.assertTrue(mock_client.send_raw_email.called)

    @patch("orchestrator.notification.SendGridAPIClient")
    def test_send_via_sendgrid(self, mock_sendgrid_client):
        mock_client = MagicMock()
        mock_sendgrid_client.return_value = mock_client

        response_mock = MagicMock()
        response_mock.status_code = 202
        response_mock.body = "Accepted"
        mock_client.send.return_value = response_mock

        smtp_client = SMTPClient("sendgrid")
        smtp_client.sendgrid_api_key = self.config["sendgrid_api_key"]
        smtp_client.send_email(
            "recipient@example.com",
            "Test Subject",
            "Test Body",
            "../../test_data/document.tar.bz2",
        )

        mock_client.send.assert_called_once()
        self.assertTrue(mock_client.send.called)

    @patch("orchestrator.notification.smtplib.SMTP")
    def test_send_via_gmail(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        smtp_client = SMTPClient("gmail")
        smtp_client.username = self.config["from_email"]
        smtp_client.password = self.config["password"]
        smtp_client.send_email(
            "recipient@example.com",
            "Test Subject",
            "Test Body",
            "../../test_data/document.tar.bz2",
        )

        mock_server.sendmail.assert_called_once()
        self.assertTrue(mock_server.sendmail.called)


if __name__ == "__main__":
    unittest.main()
