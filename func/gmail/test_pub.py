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

def get_token():
    creds = None
    if os.path.exists(USER_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(USER_TOKEN_PATH, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                OAUTH_CLIENT_PATH, 
                SCOPES, 
                redirect_uri='https://nairoki.dev'
            )
            # prompt='consent' を追加して確実にリフレッシュトークンを取得
            auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
            print(f"以下のURLをブラウザで開いてね:\n{auth_url}")
            response_url = input("認証後のURLを貼り付けてください: ")
            flow.fetch_token(authorization_response=response_url)
            creds = flow.credentials
            
        with open(USER_TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    return creds

# 起動時に認証を済ませておく
global_creds = get_token()

def get_gmail_service(creds):#Serviceに実装済み
    return build('gmail', 'v1', credentials=creds)

def get_mail_details(service, msg_id):#Processに実装済み
    """メッセージIDから送信元、件名、本文を取得"""
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = message.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "無題")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "不明")
        
        # 本文の抽出（再帰的探索）
        body = ""
        parts = [payload]
        while parts:
            part = parts.pop()
            if 'parts' in part:
                parts.extend(part['parts'])
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        
        return {"from": sender, "subject": subject, "body": body}
    except Exception as e:
        print(f"詳細取得エラー: {e}")
        return None

HISTORY_DB=[]
processed_msg_ids = set()

def get_last_history_id():#Processに実装済み
    if len(HISTORY_DB) > 0:
            return HISTORY_DB[-1]
    return None

def save_history_id(history_id):#Processに実装済み
    HISTORY_DB.append(history_id)

def callback(message):#Processに実装済み
    try:
        data = json.loads(message.data.decode("utf-8"))
        new_history_id = data.get("historyId")
        start_history_id = get_last_history_id()
        
        if not start_history_id:
            print(f"初期化: HistoryID {new_history_id} を保存")
            save_history_id(new_history_id)
            message.ack()
            return

        service = get_gmail_service(global_creds)

        # 履歴の取得
        try:
            history_results = service.users().history().list(
                userId='me',
                startHistoryId=start_history_id,
                historyTypes=['messageAdded']
            ).execute()
        except Exception as e:
            # 履歴が古すぎる(404)場合は最新1件取得に切り替える等の対策が必要
            print(f"HistoryId Expired: {e}. Resetting to latest.")
            save_history_id(new_history_id)
            message.ack()
            return

        histories = history_results.get('history', [])
        if histories:
            for h in histories:
                for m_item in h.get('messagesAdded', []):
                    msg_id = m_item['message']['id']
                    if msg_id in processed_msg_ids:
                        print(f"Skipping: すでに処理済みのメッセージです ({msg_id})")
                        continue
                    details = get_mail_details(service, msg_id)
                    if details:
                        process_mail(details)
                        processed_msg_ids.add(msg_id)
                        if len(processed_msg_ids) > 100:
                            processed_msg_ids.pop()

        save_history_id(new_history_id)
        message.ack()

    except Exception as e:
        print(f"Callback Error: {e}")
        message.ack()

def process_mail(details):#Processに実装済み
    print(f"\n--- 新着メール受信 ---")
    print(f"From: {details['from']}")
    print(f"Subject: {details['subject']}")
    
    # 金額抽出テスト（例：楽天カード）
    # amount_match = re.search(r"利用金額：([\d,]+)円", details['body'])
    # if amount_match:
    #     print(f"金額検知: {amount_match.group(1)}円")

def start_listening(): #Serviceに実装済み
    subscriber = pubsub_v1.SubscriberClient.from_service_account_json(SERVICE_KEY_PATH)
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
    
    print(f"購読開始中... {subscription_path}")
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
        print("\n購読終了")

def setup_gmail_watch(creds):#Serviceに実装済み
    service = get_gmail_service(creds)
    
    # 自分のプロジェクトのトピック名を指定
    # projects/PROJECT_ID/topics/TOPIC_ID の形式
    TOPIC_NAME = f"projects/{PROJECT_ID}/topics/{GCP_TOPIC_ID}" # ← ここを書き換える
    
    request_body = {
        'topicName': TOPIC_NAME,
        'labelIds': ['INBOX'], # 受信トレイに変化があった時だけ通知
    }
    
    # watchを実行
    response = service.users().watch(userId='me', body=request_body).execute()
    
    print(f"Watch開始: {response}")
    # response['historyId'] が返ってくるので、これを初期の history_id として保存してもOK
    save_history_id(response['historyId'])



if __name__ == "__main__":
    setup_gmail_watch(global_creds)
    start_listening()