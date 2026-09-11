from abc import ABC, abstractmethod


class BaseHandler(ABC):
    def __init__(self, sender):
        self.sender = sender
        self.address = ""

    @abstractmethod
    async def handle(self, details: dict):
        """Handle one received Gmail message."""
