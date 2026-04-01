from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Awaitable
import asyncio
@dataclass
class Job:
    id: str
    cb: Callable
    next_run: datetime
    jitter: float | None
    task: asyncio.Task | None = None
    status: str = "scheduled"  # scheduled / running / done / cancelled