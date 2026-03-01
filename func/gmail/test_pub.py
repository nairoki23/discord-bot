import json
from google.cloud import pubsub_v1
from dotenv import dotenv_values
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
config = dotenv_values(".env")
# 設定項目（自分の環境に合わせて書き換えてください）
PROJECT_ID = config["GCP_PROJECT_ID"]
SUBSCRIPTION_ID = config["GCP_SUBSCRIPTION_ID"]
# 権限スコープ（メールの読み取り専用）
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

SERVICE_KEY_PATH = "./.gcp_keys/credentials.json"
OAUTH_CLIENT_PATH= "./.gcp_keys/OAuthClient.json"
USER_TOKEN_PATH= "./.gcp_keys/token.json"

def get_gmail_service():
    creds = None
    # 以前生成した token.json があれば読み込む
    if os.path.exists(USER_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(USER_TOKEN_PATH, SCOPES)
    
    # 期限切れ、または初回の場合
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # credentials.json はGCPからダウンロードしたOAuth用ファイル
            flow = InstalledAppFlow.from_client_secrets_file(
                OAUTH_CLIENT_PATH, 
                SCOPES, 
                redirect_uri='https://nairoki.dev' # 実際にはどこでもいい
            )

            auth_url, _ = flow.authorization_url(access_type='offline')
            print(f"以下のURLをブラウザで開いてね:\n{auth_url}")

            # ブラウザで認証後、真っ白なページ（localhost）に飛ばされるので、
            # その時のブラウザの「URL欄の文字列」をコピーしてここに貼り付ける
            response_url = input("認証後にブラウザのURL欄に表示されたURLを貼り付けてください: ")

            # URLからトークンを抽出して完了！
            flow.fetch_token(authorization_response=response_url)
            creds = flow.credentials
            
        with open(USER_TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    # Gmail API サービスを構築して返す
    return build('gmail', 'v1', credentials=creds)




def callback(message):
    print("--- メッセージを受信しました ---")
    # message.data はバイト列なのでデコード
    message.ack()
    data = message.data.decode("utf-8")
    print(f"受信データ: {data}")
    # 1. Gmail APIサービスを呼び出す (以前作成したtoken.jsonを使用)
    service = get_gmail_service() 
    
    # 2. 最新のメッセージを1件取得してみるテスト
    results = service.users().messages().list(userId='me', q='is:unread', maxResults=1).execute()
    messages = results.get('messages', [])
    if messages:
        msg = service.users().messages().get(userId='me', id=messages[0]['id']).execute()
        print(f"内容: {msg['snippet']}")
    # ここでACK（確認応答）を返さないと、同じメッセージが何度も届きます
    
    print("-------------------------------")

def start_listening(): 
    subscriber = pubsub_v1.SubscriberClient.from_service_account_json(SERVICE_KEY_PATH)
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_ID)
    
    print(f"購読開始中... {subscription_path}")
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    
    try:
        # メッセージが来るのをずっと待ち続ける
        streaming_pull_future.result()
    except KeyboardInterrupt:
        # Ctrl+C で終了
        streaming_pull_future.cancel()
        print("\n購読を終了しました")

if __name__ == "__main__":
    start_listening()