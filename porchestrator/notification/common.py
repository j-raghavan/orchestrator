import logging
from abc import ABC, abstractmethod


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

    def __init__(self, **kwargs):
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
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def send(self):
        """
        Sends the email.

        This method must be implemented by child classes.
        """
        pass
