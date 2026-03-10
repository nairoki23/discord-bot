import os
from google.cloud import pubsub_v1
from dotenv import dotenv_values
from googleapiclient.discovery import build
from func.gmail.process import GmailProcess 

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
    def __init__(self,get_creds):
        self.get_creds=get_creds
        self.process = GmailProcess(self.service)
    
    def service(self):
        return build('gmail', 'v1', credentials=self.get_creds())

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
    

    def start_listening(self): 
        subscriber = pubsub_v1.SubscriberClient.from_service_account_json(SERVICE_KEY_PATH)
        subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
        
        print(f"購読開始中... {subscription_path}")
        streaming_pull_future = subscriber.subscribe(subscription_path, callback=self.process.sub_callback)
        
        try:
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()
            print("\n購読終了")
