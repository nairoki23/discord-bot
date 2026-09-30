import asyncio
import unittest
from datetime import datetime, timedelta

from service.timer.timer import TimerService


class TimerServiceCancelTest(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_removes_job_without_callback_error(self):
        loop = asyncio.get_running_loop()
        errors = []
        loop.set_exception_handler(lambda _loop, context: errors.append(context))

        timer = TimerService(loop)
        job_id = timer.schedule(datetime.now() + timedelta(hours=1), lambda: None)

        self.assertTrue(timer.cancel(job_id))
        self.assertNotIn(job_id, timer.list_jobs())

        # キャンセルされた task の done callback を実行させる
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        self.assertEqual(errors, [])
        self.assertIsNone(timer.get_status(job_id))

    async def test_cancel_unknown_job_returns_false(self):
        timer = TimerService(asyncio.get_running_loop())
        self.assertFalse(timer.cancel("unknown"))

    async def test_finished_job_is_removed(self):
        timer = TimerService(asyncio.get_running_loop())
        job_id = timer.schedule(datetime.now(), lambda: None)

        await asyncio.sleep(0.05)

        self.assertNotIn(job_id, timer.list_jobs())


if __name__ == "__main__":
    unittest.main()
