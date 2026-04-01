import os
from google.cloud import pubsub_v1
from dotenv import dotenv_values
from googleapiclient.discovery import build
from service.gmail.process import GmailProcess
import asyncio

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

class GmailService:
    def __init__(self,get_creds,loop):
        self.get_creds=get_creds
        self.process = GmailProcess(self.service)
        self.loop=loop
        self.streaming=None

    def service(self):
        return build('gmail', 'v1', credentials=self.get_creds())

    def set_handler(self,handler):
        return self.process.set_handler(handler)

    def del_handler(self,address):
        self.process.del_handler(address)
    def state_handler(self):
        return self.process.state_handler()

    def setup_gmail_watch(self):
        TOPIC_NAME = f"projects/{PROJECT_ID}/topics/{GCP_TOPIC_ID}" # ← ここを書き換える
        request_body = {
            'topicName': TOPIC_NAME,
            'labelIds': ['INBOX'], # 受信トレイに変化があった時だけ通知
        }
        response = self.service().users().watch(userId='me', body=request_body).execute()
        print(f"Watch開始: {response}")
        self.process.set_history_id(response['historyId'])
        return True
    

    def callback(self,message):
        asyncio.run_coroutine_threadsafe(
            self.process.sub_callback(message), 
            self.loop
        )

    def start_listening(self): 
        subscriber = pubsub_v1.SubscriberClient.from_service_account_json(SERVICE_KEY_PATH)
        subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
        
        if self.streaming:
            self.streaming.cancel()
            print("前セッションの購読終了。")
        
        print(f"購読開始中... {subscription_path}")
        self.streaming=subscriber.subscribe(subscription_path, callback=self.callback)
        
        # 2. 【重要】 .result() は絶対に呼ばない。
        # 代わりに、何らかの理由でスレッドが止まった時の処理だけ登録しておく
        def callback(future):
            print(f"Streaming pull future exited with: {future.exception()}")

        self.streaming.add_done_callback(callback)
