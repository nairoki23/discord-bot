from abc import ABC, abstractmethod

class BaseHandler(ABC):
    def __init__(self,sender):
        """
        初期化関数。
        Botインスタンスなどを保持し、Discord送信の準備などを整える。
        """
        self.sender=sender
        self.address=""

    @abstractmethod
    async def handle(self, details: dict):
        """
        メール受信時に叩かれるメイン関数。
        各ハンドラーで必ず実装（オーバーライド）する必要がある。
        """
        pass