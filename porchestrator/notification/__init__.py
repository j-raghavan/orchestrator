from typing import Callable, Dict

Notifier = Callable[[str], None]
_notifiers: Dict[str, type] = {}


def register_notifier(name: str) -> Callable[[type], type]:
    """
    Decorator function to register a class as a notifier.

    Args:
        name (str): The name of the notifier.

    Returns:
        Callable[[type], type]: The decorator function.

    Raises:
        TypeError: If the provided name is not a class.

    Example:
        @register_notifier("EmailNotifier")
        class EmailNotifier:
            pass

        The above code registers the `EmailNotifier` class as a
        notifier with the name "EmailNotifier".
    """

    def decorator(cls: type) -> type:
        if not isinstance(cls, type):
            raise TypeError("Only classes can be registered as notifiers.")
        _notifiers[name] = cls
        return cls

    return decorator


def get_notifier(name: str) -> type:
    """
    Retrieves a registered notifier class by its name.

    Args:
        name (str): The name of the notifier.

    Returns:
        type: The registered notifier class.

    Raises:
        ValueError: If the specified notifier is not registered.

    Example:
        notifier_class = get_notifier("EmailNotifier")
        email_notifier = notifier_class()
        email_notifier.send_notification("Hello, world!")

        The above code retrieves the `EmailNotifier` class and creates an
        instance to send a notification.
    """
    if name not in _notifiers:
        raise ValueError(f"Notifier '{name}' is not registered.")

    return _notifiers[name]
