from abc import ABC, abstractmethod


class BaseHandler(ABC):
    def __init__(self, sender):
        self.sender = sender
        self.address = ""
        # True なら From のアドレスに self.address を含むメールを扱う（大文字小文字は区別しない）
        self.partial_match = False

    @abstractmethod
    async def handle(self, details: dict):
        """Handle one received Gmail message."""
