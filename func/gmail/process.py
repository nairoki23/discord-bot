import json
from email.utils import parseaddr
class GmailProcess:
    def __init__(self,service):
        self.service = service
        self.history_ids=[]
        self.msg_ids=[]
        self.handler={}

    def set_handler(self,handlers):
        self.handler=handlers

    def state_handler(self):
        return sum(1 for h in self.handler.values() if h.sender is not None)
    def set_history_id(self,history_id):
        self.history_ids.append(history_id)

    def get_mail_details(self, msg_id):
        try:
            msg = self.service().users().messages().get(userId='me', id=msg_id, format='full').execute()
            payload = msg.get('payload', {})
            headers = payload.get('headers', [])
            labels = msg.get('labelIds', [])  # ラベル一覧を取得
            
            return {
                "id": msg_id,
                "from": next((h['value'] for h in headers if h['name'] == 'From'), ""),
                "subject": next((h['value'] for h in headers if h['name'] == 'Subject'), ""),
                "snippet": msg.get('snippet', ""),
                "is_unread": "UNREAD" in labels,
                "payload": payload  # これをそのまま Handler に渡す
            }
        except Exception as e:
            return None


    async def process_message(self, msg_id):
        if msg_id in self.msg_ids:
            print(f"Skipping: すでに処理済みのメッセージです ({msg_id})")
            return
        self.msg_ids.append(msg_id)
        details = self.get_mail_details(msg_id)
        if not details:
            print(f"詳細取得失敗: {msg_id}")
            return
        address = parseaddr(details['from'])[1]  # メールアドレスだけを抽出
        if address in self.handler:
            await self.handler[address].handle(details)  # メタデータとペイロードを渡す

        if len(self.msg_ids) > 100:
            self.msg_ids.pop()
        return details

    def diff_history(self, new_history_id):
        if len(self.history_ids)==0:
            print(f"初期化: HistoryID {new_history_id} を保存")
            return
        start_history_id = self.history_ids[-1] if self.history_ids else None
        self.set_history_id(new_history_id)
        try:
            history_results = self.service().users().history().list(
                userId='me',
                startHistoryId=start_history_id,
                historyTypes=['messageAdded']
            ).execute()
        except Exception as e:
            print(f"HistoryId Expired: {e}. Resetting to latest.")
            return
        return history_results.get('history', [])

    async def sub_callback(self, message):
        try:
            message.ack()
            new_history_id = json.loads(message.data.decode("utf-8")).get("historyId")
            histories= self.diff_history(new_history_id)
            if histories:
                for h in histories:
                    for m_item in h.get('messagesAdded', []):
                        await self.process_message(m_item['message']['id'])
        except Exception as e:
            print(f"Callback Error: {e}")
