"""指定した Gmail メッセージを登録済み handler でテストする。

Usage:
    python -m service.google.gmail.test_message --list
    python -m service.google.gmail.test_message --list --query 'from:mail@example.com'
    python -m service.google.gmail.test_message <gmail-message-id>

通知は ``DEBUG_WEBHOOK`` に送られるため、本番の Discord 通知チャンネルには
送信されない。メールの取得には通常どおり OAuth 認証済みの Google アカウントを使う。
"""

import argparse
import asyncio

from dotenv import dotenv_values

from service.google import GoogleAuth
from service.google.gmail.service import GmailService
from utils.debug import send
import utils.gmail_handlers as handlers


def register_handlers(service):
    """本番起動時と同じメール送信元の handler を登録する。"""
    service.set_handler(handlers.my.MyHandler(send))
    service.set_handler(handlers.paypay_insurance.PayPayInsuranceHandler(send))
    service.set_handler(handlers.rakuten_ticket.RakutenTicketHandler(send))
    service.set_handler(handlers.eplus.EplusHandler(send))
    service.set_handler(handlers.paypay_fleamarket.PayPayFleamarketHandler(send))
    for address in handlers.credit_card.CreditCardHandler.ADDRESSES:
        service.set_handler(
            handlers.credit_card.CreditCardHandler(send, address, service.mark_as_read)
        )

    config = dotenv_values(".env")
    for address in config.get("GMAIL_TRACK_ADDRESSES", "").split(","):
        address = address.strip()
        if address:
            service.set_handler(handlers.generic.GenericHandler(send, address))


async def list_messages(service, query, max_results):
    """テスト対象を選ぶため、最近のメールの API message ID を表示する。"""
    response = service.service().users().messages().list(
        userId="me", q=query or None, maxResults=max_results
    ).execute()
    messages = response.get("messages", [])
    if not messages:
        print("該当するメールはありません")
        return

    for message in messages:
        details = service.process.get_mail_details(message["id"])
        if details:
            print(f"{message['id']}\t{details['from']}\t{details['subject']}")


async def main(message_id=None, *, query=None, max_results=10):
    auth = GoogleAuth()
    if auth.get_creds() is None:
        raise RuntimeError("Google OAuth の認証情報がありません")

    service = GmailService(auth.get_creds, asyncio.get_running_loop())
    register_handlers(service)
    if message_id is None:
        await list_messages(service, query, max_results)
        return

    details = await service.process.process_message(message_id)
    if details is None:
        raise RuntimeError(f"Gmail メッセージを取得できませんでした: {message_id}")

    print(f"テスト済み: {details['from']} / {details['subject']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="指定した Gmail メールを handler でテストします")
    parser.add_argument("message_id", nargs="?", help="Gmail API の message ID")
    parser.add_argument("--list", action="store_true", help="最近のメールと message ID を表示する")
    parser.add_argument("--query", help="Gmail 検索構文（例: from:mail@example.com）")
    parser.add_argument("--max-results", type=int, default=10, help="一覧に出す最大件数（既定: 10）")
    args = parser.parse_args()
    if args.list == (args.message_id is not None):
        parser.error("message_id を1つ指定するか、--list を指定してください")
    asyncio.run(main(args.message_id, query=args.query, max_results=args.max_results))
