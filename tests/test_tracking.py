import unittest
from datetime import datetime
from unittest.mock import patch

from func.tracking import track as track_module
from func.tracking.model.brand import Brand
from func.tracking.model.detail import Detail
from func.tracking.model.pack import Pack
from func.tracking.model.state import State
from func.tracking.track import (
    MAX_FETCH_FAILURES,
    AlreadyTrackingError,
    FetchError,
    Track,
)


class FakeTimer:
    def __init__(self):
        self.jobs = {}
        self.cancelled = []

    def schedule(self, when, cb, jitter=None):
        job_id = f"job-{len(self.jobs)}"
        self.jobs[job_id] = cb
        return job_id

    def cancel(self, job_id):
        self.cancelled.append(job_id)
        return self.jobs.pop(job_id, None) is not None


def make_pack(*titles, state_type=State.other):
    return Pack(
        brand=Brand.yamato,
        num="1234",
        state_title=titles[-1],
        state_type=state_type,
        details=[
            Detail(title=t, place_name="営業所", time=datetime(2026, 9, 29, 10, i))
            for i, t in enumerate(titles)
        ],
    )


class FakeFetcher:
    """呼ばれるたびに responses を先頭から返す。Exception なら raise する。"""

    def __init__(self, *responses):
        self.responses = list(responses)

    async def __call__(self, num):
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class TrackingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.timer = FakeTimer()
        patcher = patch.object(track_module, "get_timer", return_value=self.timer)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.track = Track()
        self.notified = []

    def use_fetcher(self, *responses):
        patcher = patch.object(track_module, "fetch_yamato", FakeFetcher(*responses))
        patcher.start()
        self.addCleanup(patcher.stop)

    async def cb(self, pack):
        self.notified.append(pack)

    async def start(self):
        return await self.track.start_track("1234", Brand.yamato, "荷物", self.cb)

    async def run_job(self):
        (job,) = self.timer.jobs.values()
        return await job()

    async def test_start_returns_current_pack_without_notifying(self):
        self.use_fetcher(make_pack("荷物受付"))

        _, pack = await self.start()

        self.assertEqual(pack.state_title, "荷物受付")
        self.assertEqual(pack.name, "荷物")
        self.assertEqual(self.notified, [])
        self.assertEqual(len(self.timer.jobs), 1)

    async def test_update_notifies_with_new_pack(self):
        self.use_fetcher(make_pack("荷物受付"), make_pack("荷物受付", "発送"))
        await self.start()

        next_run = await self.run_job()

        self.assertIsNotNone(next_run)
        self.assertEqual(len(self.notified), 1)
        self.assertEqual(self.notified[0].state_title, "発送")

    async def test_no_change_does_not_notify(self):
        self.use_fetcher(make_pack("荷物受付"), make_pack("荷物受付"))
        await self.start()

        await self.run_job()

        self.assertEqual(self.notified, [])

    async def test_arrival_notifies_once_and_allows_retracking(self):
        self.use_fetcher(
            make_pack("荷物受付"),
            make_pack("荷物受付", "配達完了", state_type=State.arrival),
            make_pack("荷物受付"),
        )
        await self.start()

        next_run = await self.run_job()

        self.assertIsNone(next_run)
        self.assertEqual([p.state_title for p in self.notified], ["配達完了"])
        self.assertEqual(self.track.list_tracks(), [])
        await self.start()
        self.assertEqual(len(self.track.list_tracks()), 1)

    async def test_already_arrived_is_not_scheduled_or_kept(self):
        self.use_fetcher(make_pack("配達完了", state_type=State.arrival))

        _, pack = await self.start()

        self.assertEqual(pack.state_type, State.arrival)
        self.assertEqual(self.timer.jobs, {})
        self.assertEqual(self.notified, [])
        self.assertEqual(self.track.list_tracks(), [])

    async def test_duplicate_start_raises(self):
        self.use_fetcher(make_pack("荷物受付"))
        await self.start()

        with self.assertRaises(AlreadyTrackingError):
            await self.start()

    async def test_initial_fetch_failure_raises_and_is_not_kept(self):
        self.use_fetcher(RuntimeError("html changed"), make_pack("荷物受付"))

        with self.assertRaises(FetchError):
            await self.start()

        self.assertEqual(self.track.list_tracks(), [])
        await self.start()

    async def test_fetch_returning_none_is_failure(self):
        self.use_fetcher(None)

        with self.assertRaises(FetchError):
            await self.start()

    async def test_transient_failure_keeps_tracking(self):
        self.use_fetcher(
            make_pack("荷物受付"),
            RuntimeError("timeout"),
            make_pack("荷物受付", "発送"),
        )
        await self.start()

        self.assertIsNotNone(await self.run_job())
        self.assertIsNotNone(await self.run_job())

        self.assertEqual([p.state_title for p in self.notified], ["発送"])

    async def test_repeated_failures_notify_none_and_stop(self):
        self.use_fetcher(make_pack("荷物受付"), *[RuntimeError("down")] * MAX_FETCH_FAILURES)
        await self.start()

        results = [await self.run_job() for _ in range(MAX_FETCH_FAILURES)]

        self.assertIsNone(results[-1])
        self.assertTrue(all(r is not None for r in results[:-1]))
        self.assertEqual(self.notified, [None])
        self.assertEqual(self.track.list_tracks(), [])

    async def test_callback_error_does_not_stop_tracking(self):
        self.use_fetcher(make_pack("荷物受付"), make_pack("荷物受付", "発送"))

        async def broken_cb(pack):
            raise RuntimeError("discord down")

        await self.track.start_track("1234", Brand.yamato, "荷物", broken_cb)

        self.assertIsNotNone(await self.run_job())

    async def test_stop_cancels_job(self):
        self.use_fetcher(make_pack("荷物受付"))
        await self.start()

        self.assertTrue(self.track.stop_track("1234", Brand.yamato))

        self.assertEqual(self.timer.cancelled, ["job-0"])
        self.assertEqual(self.track.list_tracks(), [])
        self.assertFalse(self.track.stop_track("1234", Brand.yamato))

    async def test_one_off_fetch_failure_returns_none(self):
        self.use_fetcher(RuntimeError("html changed"))

        self.assertIsNone(await self.track.fetch_pack("1234", Brand.yamato, "荷物"))


if __name__ == "__main__":
    unittest.main()
