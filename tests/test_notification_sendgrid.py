import os
import unittest
from unittest.mock import MagicMock, patch

from porchestrator.notification.sendgrid import CustomNotifySendGrid, SendGridNotifier


class TestSendGridNotifier(unittest.TestCase):
    def setUp(self):
        self.sender = "sender@example.com"
        self.recipients = ["recipient@example.com"]
        self.subject = "Test Email"
        self.body = "This is a test email."
        test_dir = os.path.dirname(os.path.abspath(__file__))
        self.attachments = [os.path.join(test_dir, "test.txt")]

        os.environ["SENDGRID_API_KEY"] = (
            "test_api_key"  # Set the environment variable for testing
        )

        self.notifier = SendGridNotifier(
            sender=self.sender,
            recipients=self.recipients,
            subject=self.subject,
            body=self.body,
            attachments=self.attachments,
        )
        self.notifier.logger = MagicMock()

    @patch.object(CustomNotifySendGrid, "notify")
    def test_send(self, mock_notify):
        mock_notify.return_value = True  # Simulate successful notification
        self.notifier.send(self.attachments)
        self.notifier.logger.info.assert_called_with("Sending email using SendGrid")

    @patch.object(CustomNotifySendGrid, "notify")
    def test_send_failure(self, mock_notify):
        mock_notify.return_value = False  # Simulate notification failure
        with self.assertRaisesRegex(Exception, "Failed to send notification"):
            self.notifier.send()

    def test_init(self):
        self.assertEqual(self.notifier.body, self.body)
        self.assertEqual(self.notifier.subject, self.subject)
        self.assertEqual(self.notifier.apobj.api_key, "test_api_key")
        self.assertEqual(self.notifier.apobj.from_email, self.sender)
        self.assertEqual(self.notifier.apobj.to_email, ", ".join(self.recipients))


if __name__ == "__main__":
    unittest.main()
