from abc import ABC, abstractmethod
from email.mime.application import MIMEApplication

from prefect import get_run_logger


# Create a common Email class that can be used by all email providers:
class EmailNotifier(ABC):
    """
    An abstract EmailNotifier class that can be used by all email providers.

    Attributes:
        sender (str): The email address of the sender.
        recipients (list): A list of email addresses of the recipients.
        subject (str): The subject of the email.
        body_template (str): The body template of the email, which can
        be rendered using Jinja2. attachments (list): A list of file
        paths for attachments.

    Methods:
        render_body: Renders the body template using Jinja2.
        send: Sends the email. This method must be implemented by child classes.
    """

    def __init__(self, sender, recipients, subject, body_template, attachments=None):
        """
        Initializes an Email object.

        Args:
            sender (str): The email address of the sender.
            recipients (list): A list of email addresses of the recipients.
            subject (str): The subject of the email.
            body_template (str): The body template of the email, which can be
            rendered using Jinja2. attachments (list, optional): A list of file
            paths for attachments. Defaults to None.
        """
        self.sender = sender
        self.recipients = recipients
        self.subject = subject
        self.body_template = body_template
        self.attachments = attachments
        self.logger = get_run_logger()

    @abstractmethod
    def send(self):
        """
        Sends the email.

        This method must be implemented by child classes.
        """
        pass

    def attach_files(self, msg):
        """
        Attaches files to the email message.

        Args:
            msg (MIMEMultipart): The email message object.
        """
        if self.attachments:
            for attachment in self.attachments:
                with open(attachment, "rb") as file:
                    part = MIMEApplication(file.read())
                    part.add_header(
                        "Content-Disposition", "attachment", filename=attachment
                    )
                    msg.attach(part)
            self.logger.debug(f"Attachments added to the email: {self.attachments}")
        else:
            self.logger.debug("No attachments provided for the email.")
