import asyncio
from func.gmail.auth import GmailAuth
from func.gmail.service import GmailService
from func.gmail.process import GmailProcess 

async def main():
    # 1. 現在の実行ループを取得（これが実行エンジンになる）
    loop = asyncio.get_running_loop()
    
    auth = GmailAuth()
    
    # 2. ServiceとProcessを紐付け
    # ここで loop を渡す（run_coroutine_threadsafeの宛先）
    service = GmailService(auth.get_creds, None, loop=loop)
    
    # 3. Gmail設定と待機開始
    service.setup_gmail_watch()
    service.start_listening()
    
    print("Gmail監視テスト中... (Ctrl+Cで終了)")
    
    # 4. プログラムが終わらないように無限待機
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("テストを終了します")