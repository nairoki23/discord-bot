from service.gmail.HandlerBase import BaseHandler
import base64
from discord import Embed, Color


class GenericHandler(BaseHandler):
    """
    動的に追跡メルアドを登録するための汎用ハンドラー。
    整形はせず、件名・送り主・本文をEmbedで見やすく表示する。
    """
    def __init__(self, sender, address):
        super().__init__(sender)
        self.address = address

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

        # 2000文字制限に収める
        if len(text) > 500:
            text = text[:500] + "\n…(省略)"

        subject = details.get("subject", "(件名なし)")
        sender = details.get("from", "(不明)")

        embed = Embed(
            title=subject,
            description=text,
            color=Color.blue(),
        )
        embed.add_field(name="差出人", value=sender, inline=False)
        embed.set_footer(text=f"追跡対象: {self.address}")

        await self.sender(
            content=f"📩 **{subject}**",
            embed=embed,
        )
