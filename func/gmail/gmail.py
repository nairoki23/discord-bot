import json
import os
import os.path
import base64
import re
from google.cloud import pubsub_v1
from dotenv import dotenv_values
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 環境変数の読み込み
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # HTTPでのテストを許可
config = dotenv_values(".env")

PROJECT_ID = config["GCP_PROJECT_ID"]
SUBSCRIPTION_ID = config["GCP_SUBSCRIPTION_ID"]
GCP_TOPIC_ID= config["GCP_TOPIC_ID"]
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

SERVICE_KEY_PATH = "./.gcp_keys/credentials.json"
OAUTH_CLIENT_PATH = "./.gcp_keys/OAuthClient.json"
USER_TOKEN_PATH = "./.gcp_keys/token.json"
HISTORY_FILE = "last_history_id.txt"

class Gmail:
    def __init__(self):
        self.history_ids=[]
        self.msg_ids=[]
        self.creds = self.get_creds()
        if self.creds is None:
            pass
            return 
        self.service=build('gmail', 'v1', credentials=self.creds)
        self.setup_gmail_watch()
        
    def setup_gmail_watch(self):
        TOPIC_NAME = f"projects/{PROJECT_ID}/topics/{GCP_TOPIC_ID}" # ← ここを書き換える
        request_body = {
            'topicName': TOPIC_NAME,
            'labelIds': ['INBOX'], # 受信トレイに変化があった時だけ通知
        }
        response = self.service.users().watch(userId='me', body=request_body).execute()
        print(f"Watch開始: {response}")
        self.history_ids.append(response['historyId'])
        return True
    

    def process_history(self, history_id):
        for m_item in h.get('messagesAdded', []):
            msg_id = m_item['message']['id']
            if msg_id in self.msg_ids:
                print(f"Skipping: すでに処理済みのメッセージです ({msg_id})")
                continue
            details = self.get_mail_details(msg_id)
            if details:
                process_mail(details)
                self.msg_ids.append(msg_id)
                if len(self.msg_ids) > 100:
                    self.msg_ids.pop()




    def callback(self, message):
        try:
            data = json.loads(message.data.decode("utf-8"))
            new_history_id = data.get("historyId")
            if len(self.history_ids):
                print(f"初期化: HistoryID {new_history_id} を保存")
                self.history_ids.append(new_history_id)
                message.ack()
                return
            start_history_id = self.history_ids[-1] if self.history_ids else None
            try:
                history_results = self.service.users().history().list(
                    userId='me',
                    startHistoryId=start_history_id,
                    historyTypes=['messageAdded']
                ).execute()
            except Exception as e:
                print(f"HistoryId Expired: {e}. Resetting to latest.")
                self.history_ids.append(new_history_id)
                message.ack()
                return
            histories = history_results.get('history', [])
            if histories:
                for h in histories:
                    self.process_history(h)
            self.history_ids.append(new_history_id)
            message.ack()

        except Exception as e:
            print(f"Callback Error: {e}")
            message.ack()










    def start_listening(self): 
        subscriber = pubsub_v1.SubscriberClient.from_service_account_json(SERVICE_KEY_PATH)
        subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
        
        print(f"購読開始中... {subscription_path}")
        streaming_pull_future = subscriber.subscribe(subscription_path, callback=self.callback)
        
        try:
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()
            print("\n購読終了")





    def get_mail_details(self, msg_id):
        """
        メッセージのメタデータと構造（payload）をそのまま返す
        解析は後続の Handler に任せる
        """
        try:
            msg = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
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
    