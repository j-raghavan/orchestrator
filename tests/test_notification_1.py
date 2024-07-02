import pytest
import os
from unittest.mock import patch, MagicMock
from orchestrator.notification import SMTPClient

@pytest.fixture
def attachment_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '../test_data/document.tar.bz2'))

def test_send_via_aws_ses(attachment_path):
    with patch('orchestrator.notification.boto3.client') as mock_boto_client:
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        smtp_client = SMTPClient('aws_ses')
        smtp_client.send_email('recipient@example.com', 'Test Subject', 'Test Body', attachment_path)

        mock_client.send_raw_email.assert_called_once()
        assert mock_client.send_raw_email.called

def test_send_via_sendgrid(attachment_path):
    with patch('orchestrator.notification.SendGridAPIClient') as mock_sendgrid_client:
        mock_client = MagicMock()
        mock_sendgrid_client.return_value = mock_client

        response_mock = MagicMock()
        response_mock.status_code = 202
        response_mock.body = "Accepted"
        mock_client.send.return_value = response_mock

        smtp_client = SMTPClient('sendgrid')
        smtp_client.send_email('recipient@example.com', 'Test Subject', 'Test Body', attachment_path)

        mock_client.send.assert_called_once()
        assert mock_client.send.called

def test_send_via_gmail(attachment_path):
    with patch('orchestrator.notification.smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        smtp_client = SMTPClient('gmail')
        smtp_client.send_email('recipient@example.com', 'Test Subject', 'Test Body', attachment_path)

        mock_server.sendmail.assert_called_once()
        assert mock_server.sendmail.called
