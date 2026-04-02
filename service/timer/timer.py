import asyncio
import random
import uuid
from datetime import datetime, timedelta
from .job import Job

class TimerService:
    def __init__(self,loop: asyncio.AbstractEventLoop):
        self.jobs: dict[str, Job] = {}
        self.loop = loop

    def schedule(self, when: datetime, cb, jitter: timedelta | None = None) -> str:
        job_id = str(uuid.uuid4())

        job = Job(
            id=job_id,
            cb=cb,
            next_run=when,
            jitter=jitter.total_seconds() if jitter else None,
        )

        task = self.loop.create_task(self._run(job))
        job.task = task

        self.jobs[job_id] = job
        task.add_done_callback(lambda t: self._on_done(job_id))

        return job_id

    async def _run(self, job: Job):
        while True:
            job.next_run = self._apply_jitter(job.next_run, job.jitter)

            now = datetime.now()
            delay = (job.next_run - now).total_seconds()

            if delay > 0:
                await asyncio.sleep(delay)

            job.status = "running"

            try:
                result = await self._maybe_await(job.cb())
            except Exception as e:
                job.status = "done"
                print(f"[{job.id}] error: {e}")
                return

            if result is None:
                job.status = "done"
                return

            job.status = "scheduled"
            job.next_run = result

    def cancel(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return False

        if job.task:
            job.task.cancel()

        job.status = "cancelled"
        self._on_done(job_id)
        return True

    def get_next_run(self, job_id: str) -> datetime | None:
        job = self.jobs.get(job_id)
        return job.next_run if job else None

    def get_status(self, job_id: str) -> str | None:
        job = self.jobs.get(job_id)
        return job.status if job else None

    def list_jobs(self):
        return {
            job_id: {
                "next_run": job.next_run,
                "status": job.status,
            }
            for job_id, job in self.jobs.items()
        }

    def _on_done(self, job_id: str):
        # 完全に消すならここ
        del self.jobs[job_id]

        # 履歴残すなら何もしない
        pass

    def _apply_jitter(self, when: datetime, jitter: float | None):
        if not jitter:
            return when
        offset = random.uniform(0, jitter)
        return when + timedelta(seconds=offset)

    async def _maybe_await(self, result):
        if asyncio.iscoroutine(result):
            return await result
        return result