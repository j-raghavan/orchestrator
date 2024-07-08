import os
import unittest
from email.mime.base import MIMEBase
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from porchestrator.notification.ses import SESNotifier


class TestSESNotifier(unittest.TestCase):
    def setUp(self):
        self.aws_access_key_id = "test_access_key"
        self.aws_secret_access_key = "test_secret_key"
        self.region_name = "us-west-2"
        self.from_email = "from@example.com"
        self.to_email = "to@example.com"
        self.subject = "Test Email"
        self.body = "This is a test email."

        self.notifier = SESNotifier(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
            from_email=self.from_email,
            to_email=self.to_email,
            subject=self.subject,
            body=self.body,
        )
        self.notifier.logger = MagicMock()

    def test_init(self):
        assert self.notifier.aws_access_key_id == self.aws_access_key_id
        assert self.notifier.aws_secret_access_key == self.aws_secret_access_key
        assert self.notifier.region_name == self.region_name
        assert self.notifier.from_email == self.from_email
        assert self.notifier.to_email == self.to_email
        assert self.notifier.subject == self.subject
        assert self.notifier.body == self.body

    @patch("boto3.client")
    def test_send(self, mock_client):
        mock_ses = MagicMock()
        mock_ses.send_raw_email.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }
        mock_client.return_value = mock_ses
        result = self.notifier.send(self.body)
        assert result is True
        self.notifier.logger.debug.assert_called_once_with(
            "Notification sent successfully"
        )

    @patch("boto3.client")
    def test_send_with_attachment(self, mock_client):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        self.attachment_path = os.path.join(test_dir, "test.txt")
        mock_ses = MagicMock()
        mock_ses.send_raw_email.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }
        mock_client.return_value = mock_ses

        with open(self.attachment_path, "w") as f:
            f.write("test")

        result = self.notifier.send(self.body, attachment_path=self.attachment_path)
        assert result is True
        self.notifier.logger.debug.assert_called_once_with(
            "Notification sent successfully"
        )

    @patch("boto3.client")
    def test_send_failure(self, mock_client):
        mock_ses = MagicMock()
        mock_ses.send_raw_email.side_effect = ClientError(
            {"Error": {"Code": "500"}}, "SendRawEmail"
        )
        mock_client.return_value = mock_ses

        result = self.notifier.send(self.body)
        assert result is False

        # Assert that the critical method was called with an error message
        self.notifier.logger.critical.assert_called_once()
        call_args = self.notifier.logger.critical.call_args[
            0
        ]  # Get arguments of the call
        self.assertIn("Error sending email notification:", call_args[0])
        self.assertIn("An error occurred (500)", call_args[0])

    @patch("boto3.client")
    def test_send_email_with_arn(self, mock_boto_client):
        mock_ses_client = MagicMock()
        mock_boto_client.return_value = mock_ses_client

        notifier = SESNotifier(
            arn="arn:aws:ses:us-west-2:123456789012:identity/example.com",
            from_email="sender@example.com",
            to_email="recipient@example.com",
            subject="Test Subject",
            body="Test Body",
        )

        mock_ses_client.send_raw_email.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        result = notifier.send("Test Body")

        self.assertTrue(result)

        args, kwargs = mock_ses_client.send_raw_email.call_args
        self.assertEqual(kwargs["Source"], "sender@example.com")
        self.assertEqual(kwargs["Destinations"], ["recipient@example.com"])
        self.assertIn("RawMessage", kwargs)
        self.assertIn("Data", kwargs["RawMessage"])
        self.assertIn("From: sender@example.com", kwargs["RawMessage"]["Data"])
        self.assertIn("To: recipient@example.com", kwargs["RawMessage"]["Data"])
        self.assertIn("Subject: Test Subject", kwargs["RawMessage"]["Data"])
        self.assertIn("Test Body", kwargs["RawMessage"]["Data"])
        self.assertEqual(
            kwargs["SourceArn"],
            "arn:aws:ses:us-west-2:123456789012:identity/example.com",
        )
        self.assertEqual(
            kwargs["FromArn"], "arn:aws:ses:us-west-2:123456789012:identity/example.com"
        )
        self.assertEqual(
            kwargs["ReturnPathArn"],
            "arn:aws:ses:us-west-2:123456789012:identity/example.com",
        )

    def test_create_attachment(self):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        self.attachment_path = os.path.join(test_dir, "test.txt")
        with open(self.attachment_path, "w") as f:
            f.write("test")
        attachment = self.notifier._create_attachment(self.attachment_path)
        assert isinstance(attachment, MIMEBase)
        assert attachment.get_filename() == os.path.basename(self.attachment_path)


if __name__ == "__main__":
    unittest.main()
