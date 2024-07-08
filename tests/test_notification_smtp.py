import os
import smtplib
import unittest
from email.mime.base import MIMEBase
from unittest.mock import MagicMock, patch

from porchestrator.notification.smtp import SMTPNotifier


class MockSMTP:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def starttls(self):
        pass

    def login(self, username, password):
        pass

    def sendmail(self, from_addr, to_addrs, msg):
        pass

    def quit(self):
        pass


class TestSMTPNotifier(unittest.TestCase):
    def setUp(self):
        self.smtp_server = "smtp.example.com"
        self.port = 587
        self.username = "testuser"
        self.password = "testpassword"
        self.from_email = "from@example.com"
        self.to_email = "to@example.com"
        self.subject = "Test Email"
        self.body = "This is a test email."
        test_dir = os.path.dirname(os.path.abspath(__file__))
        self.attachment_path = os.path.join(test_dir, "test.txt")

        self.notifier = SMTPNotifier(
            smtp_server=self.smtp_server,
            port=self.port,
            username=self.username,
            password=self.password,
            from_email=self.from_email,
            to_email=self.to_email,
            subject=self.subject,
            body=self.body,
            attachment_path=self.attachment_path,
        )
        self.notifier.logger = MagicMock()

    def test_init(self):
        assert self.notifier.smtp_server == self.smtp_server
        assert self.notifier.port == self.port
        assert self.notifier.username == self.username
        assert self.notifier.password == self.password
        assert self.notifier.from_email == self.from_email
        assert self.notifier.to_email == self.to_email
        assert self.notifier.subject == self.subject
        assert self.notifier.body == self.body
        assert self.notifier.attachment_path == self.attachment_path

    @patch("smtplib.SMTP")
    def test_send(self, mock_smtp):
        mock_smtp.return_value = MockSMTP(self.smtp_server, self.port)
        result = self.notifier.send(self.body)
        assert result is True
        self.notifier.logger.info.assert_called_once_with(
            f"Email sent via SMTP to {self.to_email}"
        )

    @patch("smtplib.SMTP")
    def test_send_with_attachment(self, mock_smtp):
        mock_smtp.return_value = MockSMTP(self.smtp_server, self.port)
        result = self.notifier.send(self.body, attachment_path=self.attachment_path)
        assert result is True
        self.notifier.logger.info.assert_called_once_with(
            f"Email sent via SMTP to {self.to_email}"
        )

    @patch("smtplib.SMTP")
    def test_send_failure(self, mock_smtp):
        mock_smtp.side_effect = smtplib.SMTPException("Test exception")
        result = self.notifier.send(self.body)
        assert result is False
        self.notifier.logger.critical.assert_called_once_with(
            "SMTPException occurred: Test exception"
        )

    @patch("smtplib.SMTP")
    def test_send_unexpected_error(self, mock_smtp):
        mock_smtp.side_effect = Exception("Test exception")
        result = self.notifier.send(self.body)
        assert result is False
        self.notifier.logger.critical.assert_called_once_with(
            "An unexpected error occurred: Test exception"
        )

    def test_create_attachment(self):
        attachment = self.notifier._create_attachment(self.attachment_path)
        assert isinstance(attachment, MIMEBase)
        assert attachment.get_filename() == os.path.basename(self.attachment_path)


if __name__ == "__main__":
    unittest.main()
