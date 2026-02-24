from enum import IntEnum
class State(IntEnum):
    WAIT = 1
    RUN = 2
    FIN = 3
    ERROR = 4

class Timer:
    def __init__(self,
            name: str, 
            target_time: datetime, 
            jitter_range: Tuple[float, float], 
            callback: Callable, 
            *args):

        self.name = name
        self.target_time = target_time
        self.jitter_range = jitter_range
        self.callback = callback
        self.args = args
        self.task = None  # asyncio.Task を格納
        self.status:State = 1

    async def start(self):
        try:
            # 待機時間の計算
            now = datetime.now()
            initial_delay = (self.target_time - now).total_seconds()
            
            jitter = random.uniform(*self.jitter_range)
            total_wait = max(0, initial_delay + jitter)
            
            self.status = 2
            await asyncio.sleep(total_wait)
            
            # コールバックの実行
            res=await self.callback(*self.args)
            self.status = 3
            return res
        except asyncio.CancelledError:
            self.status = 4
            raise
            return None

    def cancel(self):
        """タイマーを強制終了する"""
        if self.task and not self.task.done():
            self.task.cancel()
            self.status = 4