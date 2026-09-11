from service.google.gmail.handler_base import BaseHandler
import base64

class MyHandler(BaseHandler):
    def __init__(self, sender):
        # 親クラスの初期化（self.bot = bot が実行される）
        super().__init__(sender)
        self.address=""

    def extract_body(self, payload):
        """
        Gmail APIのpayloadから本文(text/plain)を再帰的に抽出してデコードします。
        """
        body_data = ""
        if "parts" not in payload:
            body_data = payload.get("body", {}).get("data", "")
        else:
            # 1. まずは平文(text/plain)を探す
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    body_data = part.get("body", {}).get("data", "")
                    break
            
            # 2. なければ子パートを再帰的に探索
            if not body_data:
                for part in payload["parts"]:
                    if "parts" in part:
                        body_data = self.extract_body(part)
                        if body_data:
                            break
            
            # 3. それでもなければHTML(text/html)を探す
            if not body_data:
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/html":
                        body_data = part.get("body", {}).get("data", "")
                        break

        if body_data:
            try:
                # urlsafe_b64decode でデコードし、UTF-8文字列に変換
                return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
            except Exception as e:
                print(f"Base64 decoding error: {e}")
                return ""
        return ""

    async def handle(self, details):
        text = ""
        try:
            payload = details.get("payload", {})
            text = self.extract_body(payload)
        except Exception as e:
            print(f"Body extraction error: {e}")
            
        if not text:
            text = "(本文なし)"
        print(text)
        print(details["subject"])
        await self.sender(
            content="Subject: " + details["subject"] + "\n" + text,
        )
