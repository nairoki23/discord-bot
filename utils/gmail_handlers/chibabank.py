from .base import BaseHandler
import re

class ChibabankHandler(BaseHandler):
    def __init__(self, sender):
        # 親クラスの初期化（self.bot = bot が実行される）
        super().__init__(sender)
        self.address="mail@vdebit.chibabank.co.jp"

    async def handle(self, details):
        pass