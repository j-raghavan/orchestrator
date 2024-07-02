# This tests notification
import pytest

from orchestrator.notification import SMTPClient


@pytest.mark.notification
class TestSMTPClient:
    PYTEST_MARK = "notification"

    config = {
        "aws_access_key_id": "",
        "aws_secret_access_key": "",
        "region_name": "us-west-2",
        "sendgrid_api_key": "",
        "from_email": "",
        "password": "",
    }

    def setUp(self):
        pass

    def test_send_via_aws_ses(self):
        smtp_client = SMTPClient("aws_ses")
        smtp_client.aws_access_key_id = self.config["aws_access_key_id"]
        smtp_client.aws_secret_access_key = self.config["aws_secret_access_key"]
        smtp_client.region_name = self.config["region_name"]

        ret = smtp_client.send_email(
            "test@test.com",
            "Prefect Orchestrator Test",
            "SUMMARY RESULTS",
            "test_data/document.tar.bz2",
        )

        # ret = smtp_client.send_raw_email.assert_called_once()
        print(ret)

    def test_send_via_sendgrid(self):
        smtp_client = SMTPClient("sendgrid")
        smtp_client.sendgrid_api_key = self.config["sendgrid_api_key"]

        ret = smtp_client.send_email(
            "test@test.com",
            "Prefect Orchestrator Test",
            "SUMMARY RESULTS",
            "test_data/document.tar.bz2",
        )

        # ret = smtp_client.send.assert_called_once()
        print(ret)

    def test_send_via_gmail(self):
        smtp_client = SMTPClient("gmail")
        smtp_client.username = self.config["from_email"]
        smtp_client.password = self.config["password"]

        ret = smtp_client.send_email(
            "test@test.com",
            "Prefect Orchestrator Test",
            "SUMMARY RESULTS",
            "test_data/document.tar.bz2",
        )

        # ret = smtp_client.sendmail.assert_called_once()
        print(ret)
