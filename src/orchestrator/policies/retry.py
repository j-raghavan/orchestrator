from pydantic import BaseModel


class RetryPolicy(BaseModel):
    max_attempts: int = 3
    delay_seconds: int = 5
    exponential_backoff: bool = True
    max_delay_seconds: int = 300

    def model_post_init(self, _context) -> None:
        if not 1 <= self.max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
        if not 1 <= self.delay_seconds <= 300:
            raise ValueError("delay_seconds must be between 1 and 300")
        if not 1 <= self.max_delay_seconds <= 3600:
            raise ValueError("max_delay_seconds must be between 1 and 3600")

    def get_next_delay(self, attempt: int) -> int:
        if self.exponential_backoff:
            delay = min(
                self.delay_seconds * (2 ** (attempt - 1)), self.max_delay_seconds
            )
        else:
            delay = self.delay_seconds
        return delay
