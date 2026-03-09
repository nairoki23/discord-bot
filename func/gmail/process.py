import json

HANDLERS ={}

class GmailProcess:
    def __init__(self,service):
        self.service = service
        self.history_ids=[]
        self.msg_ids=[]

    def set_history_id(self,history_id):
        self.history_ids.append(history_id)

    def get_mail_details(self, msg_id):
        """
        メッセージのメタデータと構造（payload）をそのまま返す
        解析は後続の Handler に任せる
        """
        try:
            msg = self.service().users().messages().get(userId='me', id=msg_id, format='full').execute()
            payload = msg.get('payload', {})
            headers = payload.get('headers', [])
            
            return {
                "id": msg_id,
                "from": next((h['value'] for h in headers if h['name'] == 'From'), ""),
                "subject": next((h['value'] for h in headers if h['name'] == 'Subject'), ""),
                "snippet": msg.get('snippet', ""),
                "payload": payload  # これをそのまま Handler に渡す
            }
        except Exception as e:
            return None


    def process_history(self, h):
        for m_item in h.get('messagesAdded', []):
            msg_id = m_item['message']['id']
            if msg_id in self.msg_ids:
                print(f"Skipping: すでに処理済みのメッセージです ({msg_id})")
                continue
            details = self.get_mail_details(msg_id)
            if not details:
                print(f"詳細取得失敗: {msg_id}")
                continue

            if details['from'] in HANDLERS:
                HANDLERS[details['from']](details)  # メタデータとペイロードを渡す

            self.msg_ids.append(msg_id)
            if len(self.msg_ids) > 100:
                self.msg_ids.pop()

    def sub_callback(self, message):
        try:
            message.ack()
            new_history_id = json.loads(message.data.decode("utf-8")).get("historyId")
            if len(self.history_ids)==0:
                print(f"初期化: HistoryID {new_history_id} を保存")
                return
            start_history_id = self.history_ids[-1] if self.history_ids else None
            self.set_history_id(new_history_id)
            try:
                history_results = self.service.users().history().list(
                    userId='me',
                    startHistoryId=start_history_id,
                    historyTypes=['messageAdded']
                ).execute()
            except Exception as e:
                print(f"HistoryId Expired: {e}. Resetting to latest.")
                return
            
            histories = history_results.get('history', [])
            if not histories:
                print(f"履歴なし: {new_history_id}")
            else:
                for h in histories:
                    self.process_history(h)
        except Exception as e:
            print(f"Callback Error: {e}")
