from service.gmail.HandlerBase import BaseHandler
class MyHandler(BaseHandler):
    def __init__(self, sender):
        # 親クラスの初期化（self.bot = bot が実行される）
        super().__init__(sender)
        self.address=""

    async def handle(self, details):
        await self.sender(
            content=details["subject"],
        )