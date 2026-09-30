import asyncio

from dotenv import dotenv_values
from google.cloud import pubsub_v1
from googleapiclient.discovery import build

from .process import GmailProcess


config = dotenv_values(".env")


class GmailService:
    def __init__(self, get_creds, loop):
        self.get_creds = get_creds
        self.process = GmailProcess(self.service)
        self.loop = loop
        self.streaming = None

    def service(self):
        creds = self.get_creds()
        if creds is None:
            raise RuntimeError("Googleアカウントが認証されていません")
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def set_handler(self, handler):
        return self.process.set_handler(handler)

    def del_handler(self, address):
        self.process.del_handler(address)

    def state_handler(self):
        return self.process.state_handler()

    def handler_addresses(self):
        return self.process.handler_addresses()

    def verify_connection(self):
        return self.process.verify_connection()

    def mark_as_read(self, msg_id):
        return self.process.mark_as_read(msg_id)

    def setup_gmail_watch(self):
        project_id = config.get("GCP_PROJECT_ID")
        topic_id = config.get("GCP_TOPIC_ID")
        if not project_id or not topic_id:
            raise RuntimeError("GCP_PROJECT_ID と GCP_TOPIC_ID を設定してください")
        response = self.service().users().watch(
            userId="me",
            body={
                "topicName": f"projects/{project_id}/topics/{topic_id}",
                "labelIds": ["INBOX"],
            },
        ).execute()
        self.process.set_history_id(response["historyId"])
        print(f"Gmail watch started: {response}")
        return True

    def callback(self, message):
        asyncio.run_coroutine_threadsafe(self.process.sub_callback(message), self.loop)

    def start_listening(self):
        project_id = config.get("GCP_PROJECT_ID")
        subscription_id = config.get("GCP_SUBSCRIPTION_ID")
        service_key_path = (
            config.get("GOOGLE_SERVICE_ACCOUNT_PATH")
            or "./.gcp_keys/credentials.json"
        )
        if not project_id or not subscription_id:
            raise RuntimeError("GCP_PROJECT_ID と GCP_SUBSCRIPTION_ID を設定してください")

        subscriber = pubsub_v1.SubscriberClient.from_service_account_json(service_key_path)
        subscription_path = subscriber.subscription_path(project_id, subscription_id)
        if self.streaming:
            self.streaming.cancel()

        self.streaming = subscriber.subscribe(subscription_path, callback=self.callback)

        def on_done(future):
            if not future.cancelled():
                print(f"Gmail subscription exited: {future.exception()}")

        self.streaming.add_done_callback(on_done)
