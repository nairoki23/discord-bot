"""INFORICH（CHARGESPOT / SPOTJOBS）の通知メールを整形してDiscordへ送る。"""

import base64
import re
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup
from discord import Color, Embed

from service.google.gmail.handler_base import BaseHandler


INFORICH_ADDRESS = "noreply@noreply.inforichjapan.com"
CHARGESPOT_RECEIPT_SUBJECT = "CHARGESPOTをご利用いただきましてありがとうございます。"
CHARGESPOT_COLOR = Color(0x00CDD7)
SPOTJOBS_COLOR = Color(0xFF864A)

# SPOTJOBS の件名 → (絵文字, 色)
SPOTJOBS_KINDS = {
    "SPOTJOBSご本人様確認のお知らせ": ("📄", Color.blurple()),
    "SPOTJOBS本人確認完了のおしらせ": ("✅", Color.green()),
    "SPOTJOBS本人確認書類再提出のお願い": ("⚠️", Color.orange()),
}
MAX_DESCRIPTION = 1000


class InforichHandler(BaseHandler):
    """CHARGESPOT の利用完了はオーダー内容を、それ以外は本文の段落をEmbedで送る。"""

    def __init__(self, sender):
        super().__init__(sender)
        self.address = INFORICH_ADDRESS

    @staticmethod
    def _extract_html(payload):
        if payload.get("mimeType") == "text/html":
            body_data = payload.get("body", {}).get("data", "")
            if body_data:
                return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            text = InforichHandler._extract_html(part)
            if text:
                return text
        return ""

    @staticmethod
    def _received_at(payload):
        """Date ヘッダの受信日時。読めなければ None。"""
        for header in payload.get("headers", []):
            if header.get("name", "").lower() == "date":
                try:
                    return parsedate_to_datetime(header["value"])
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _content_root(soup):
        """本文部分（ヘッダー・フッターを除く）。見つからなければ body 全体。"""
        return soup.select_one(".emailContent") or soup.body or soup

    @staticmethod
    def _items(root):
        """「<li>項目名：<span>値</span></li>」を {項目名: 値} で返す。注意書きの blockquote 内は除く。"""
        items = {}
        for li in root.find_all("li"):
            if li.find_parent("blockquote"):
                continue
            match = re.match(r"([^:：]+)[:：](.*)", li.get_text().strip(), re.S)
            if match:
                items[match.group(1).strip()] = match.group(2).strip()
        return items

    @staticmethod
    def _paragraph_text(p):
        """段落をテキストにする。リンクは Markdown にし、行頭の字下げを除く。"""
        for a in p.find_all("a", href=True):
            label = a.get_text(strip=True)
            a.replace_with(f"[{label}]({a['href']})" if label else "")
        lines = [line.strip() for line in p.get_text().splitlines()]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()

    @classmethod
    def _paragraphs(cls, root):
        """本文の段落。宛名（「〜様」）と、画像・ボタンだけの中央寄せ段落は除く。"""
        paragraphs = []
        for p in root.find_all("p"):
            if p.get("style"):
                continue
            text = cls._paragraph_text(p)
            if text and not text.endswith("様"):
                paragraphs.append(text)
        return paragraphs

    @staticmethod
    def _yen(value):
        return f"{int(value):,}円" if value.isdigit() else value

    @staticmethod
    def _truncate(text):
        if len(text) > MAX_DESCRIPTION:
            return text[:MAX_DESCRIPTION] + "\n…(省略)"
        return text

    @staticmethod
    def _add_fields(embed, fields):
        for name, value in fields:
            if value:
                embed.add_field(name=name, value=value, inline=True)

    def _build_receipt(self, root):
        items = self._items(root)
        amount = self._yen(items.get("利用金額（円）", ""))
        rent_at = items.get("貸出場所", "")
        return_at = items.get("返却場所", "")
        description = f"モバイルバッテリーを返却しました（{amount}）" if amount else "モバイルバッテリーを返却しました"
        embed = Embed(title="CHARGESPOT 利用完了", description=description, color=CHARGESPOT_COLOR)
        self._add_fields(embed, [
            ("利用金額", amount),
            ("貸出場所", rent_at),
            ("返却場所", return_at),
            ("決済方法", items.get("決済方法", "")),
            ("オーダー番号", items.get("オーダー番号", "")),
        ])
        embed.set_footer(text="CHARGESPOT")
        return "🔋", embed

    def _build_notice(self, subject, root):
        """本文の段落をそのまま載せる。SPOTJOBS の既知の件名は絵文字と色を変える。"""
        heading = root.find("h1")
        title = heading.get_text(strip=True) if heading else subject
        text = "\n\n".join(self._paragraphs(root)) or root.get_text("\n", strip=True)
        if subject.startswith("SPOTJOBS"):
            emoji, color = SPOTJOBS_KINDS.get(subject, ("📩", SPOTJOBS_COLOR))
            footer = "SPOTJOBS"
        else:
            emoji, color = "📩", CHARGESPOT_COLOR
            footer = "CHARGESPOT" if "CHARGESPOT" in subject else "INFORICH"
        embed = Embed(
            title=title or subject or "(件名なし)",
            description=self._truncate(text or "(本文なし)"),
            color=color,
        )
        embed.set_footer(text=footer)
        return emoji, embed

    async def handle(self, details):
        subject = details.get("subject", "")
        payload = details.get("payload", {})
        soup = BeautifulSoup(self._extract_html(payload), "html.parser")
        root = self._content_root(soup)

        if subject == CHARGESPOT_RECEIPT_SUBJECT:
            emoji, embed = self._build_receipt(root)
            content = f"{emoji} {embed.description}"
        else:
            emoji, embed = self._build_notice(subject, root)
            content = f"{emoji} **{subject or embed.title}**"
        embed.timestamp = self._received_at(payload)
        await self.sender(content=content, embed=embed)
