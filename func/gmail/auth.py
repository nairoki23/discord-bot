
import os
import os.path
from dotenv import dotenv_values
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


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

class GmailAuth:
    def __init__(self):
        self.flow = None
    def get_creds(self):
        """
        ユーザー操作なしで認証を試みる。
        有効なトークンがある、またはリフレッシュ可能な場合にのみ成功する。
        """
        creds = None
        if os.path.exists(USER_TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(USER_TOKEN_PATH, SCOPES)    
        # トークンが存在し、かつ（有効である、または期限切れだがリフレッシュ可能）な場合
        if not creds:
            return None
        elif creds.valid:
            return creds
        elif creds.expired and creds.refresh_token:
            try:
                #トークン期限切れでリフレッシュ
                creds.refresh(Request())
                # 更新された内容を保存
                with open(USER_TOKEN_PATH, 'w') as token:
                    token.write(creds.to_json())
                return creds
            except Exception as e:
                return None
        else:
            return None
    def interactive_creds(self,url):
        if self.flow is None:
            return None
        self.flow.fetch_token(authorization_response=url)
        creds = self.flow.credentials
        return creds.valid

    def create_cred_url(self):
        self.flow = InstalledAppFlow.from_client_secrets_file(
                OAUTH_CLIENT_PATH, 
                SCOPES, 
                redirect_uri='https://nairoki.dev'
        )
        # prompt='consent' を追加して確実にリフレッシュトークンを取得
        auth_url, _ = self.flow.authorization_url(access_type='offline', prompt='consent')
        return auth_url