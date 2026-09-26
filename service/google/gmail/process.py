import json
from email.utils import parseaddr


class GmailProcess:
    def __init__(self, service):
        self.service = service
        self.history_ids = []
        self.msg_ids = []
        self.handler = {}

    def set_handler(self, handler):
        if (
            handler is None
            or handler.address is None
            or handler.address in self.handler
            or handler.sender is None
        ):
            return False
        self.handler[handler.address] = handler
        return True

    def del_handler(self, address):
        del self.handler[address]

    def state_handler(self):
        return sum(1 for handler in self.handler.values() if handler.sender is not None)

    def set_history_id(self, history_id):
        self.history_ids.append(history_id)

    def mark_as_read(self, msg_id):
        try:
            self.service().users().messages().modify(
                userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            return True
        except Exception as exc:
            print(f"Failed to mark Gmail message {msg_id} as read: {exc}")
            return False

    def get_mail_details(self, msg_id):
        try:
            msg = self.service().users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
            payload = msg.get("payload", {})
            headers = payload.get("headers", [])
            labels = msg.get("labelIds", [])
            return {
                "id": msg_id,
                "from": next((h["value"] for h in headers if h["name"] == "From"), ""),
                "subject": next((h["value"] for h in headers if h["name"] == "Subject"), ""),
                "snippet": msg.get("snippet", ""),
                "is_unread": "UNREAD" in labels,
                "payload": payload,
            }
        except Exception as exc:
            print(f"Failed to fetch Gmail message {msg_id}: {exc}")
            return None

    async def process_message(self, msg_id):
        if msg_id in self.msg_ids:
            print(f"Skipping already processed message: {msg_id}")
            return None
        self.msg_ids.append(msg_id)
        details = self.get_mail_details(msg_id)
        if not details:
            return None
        address = parseaddr(details["from"])[1]
        if address in self.handler:
            await self.handler[address].handle(details)
        if len(self.msg_ids) > 100:
            self.msg_ids.pop(0)
        return details

    def diff_history(self, new_history_id):
        if not self.history_ids:
            self.set_history_id(new_history_id)
            return []
        start_history_id = self.history_ids[-1]
        self.set_history_id(new_history_id)
        try:
            response = self.service().users().history().list(
                userId="me",
                startHistoryId=start_history_id,
                historyTypes=["messageAdded"],
            ).execute()
        except Exception as exc:
            print(f"Gmail history expired or unavailable: {exc}")
            return []
        return response.get("history", [])

    async def sub_callback(self, message):
        try:
            message.ack()
            new_history_id = json.loads(message.data.decode("utf-8")).get("historyId")
            for history in self.diff_history(new_history_id):
                for item in history.get("messagesAdded", []):
                    await self.process_message(item["message"]["id"])
        except Exception as exc:
            print(f"Gmail callback failed: {exc}")
