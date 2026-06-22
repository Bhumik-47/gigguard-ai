"""
async_tasks.py - Asynchronous task processing for scalability

Implements:
- Task queue management
- Background job processing
- Task status tracking
- Async result caching
"""

import asyncio
import uuid
from typing import Any, Callable, Optional, List
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    def __init__(self, task_id: str, func: Callable, args: tuple = (), kwargs: dict = None):
        self.id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": str(self.result)[:100] if self.result else None,
            "error": str(self.error)[:100] if self.error else None,
        }


class TaskQueue:
    def __init__(self, max_queue_size: int = 1000, workers: int = 5):
        self.queue: List[Task] = []
        self.max_queue_size = max_queue_size
        self.workers = workers
        self.completed_tasks = {}
        self.stats = {
            "total_tasks": 0,
            "completed": 0,
            "failed": 0,
            "avg_execution_time": 0,
        }

    def enqueue(self, func: Callable, args: tuple = (), kwargs: dict = None) -> str:
        if len(self.queue) >= self.max_queue_size:
            raise RuntimeError("Task queue is full")

        task_id = str(uuid.uuid4())
        task = Task(task_id, func, args, kwargs or {})
        self.queue.append(task)
        self.stats["total_tasks"] += 1

        return task_id

    def get_task_status(self, task_id: str) -> Optional[Task]:
        for task in self.queue:
            if task.id == task_id:
                return task

        return self.completed_tasks.get(task_id)

    def get_queue_length(self) -> int:
        return len(self.queue)

    async def process_tasks(self):
        while self.queue:
            task = self.queue.pop(0)
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.now()

            try:
                task.result = await self._execute_task(task)
                task.status = TaskStatus.COMPLETED
                self.stats["completed"] += 1
            except Exception as e:
                task.error = str(e)
                task.status = TaskStatus.FAILED
                self.stats["failed"] += 1
            finally:
                task.completed_at = datetime.now()
                execution_time = (
                    task.completed_at - task.started_at
                ).total_seconds()
                self.completed_tasks[task.id] = task

    async def _execute_task(self, task: Task) -> Any:
        if asyncio.iscoroutinefunction(task.func):
            return await task.func(*task.args, **task.kwargs)
        else:
            return task.func(*task.args, **task.kwargs)

    def get_stats(self) -> dict:
        total_tasks = self.stats["total_tasks"]
        if total_tasks > 0:
            success_rate = (
                (self.stats["completed"] / total_tasks) * 100
            )
        else:
            success_rate = 0

        return {
            **self.stats,
            "queue_length": len(self.queue),
            "success_rate": f"{success_rate:.1f}%",
            "workers": self.workers,
        }

    def get_task_history(self, limit: int = 20) -> list:
        items = sorted(
            self.completed_tasks.items(),
            key=lambda x: x[1].completed_at or datetime.now(),
            reverse=True,
        )
        return [task.to_dict() for _, task in items[:limit]]


class BackgroundJobScheduler:
    def __init__(self):
        self.jobs = {}
        self.running = False

    def schedule_job(self, job_name: str, func: Callable, interval: int):
        self.jobs[job_name] = {
            "func": func,
            "interval": interval,
            "last_run": None,
            "run_count": 0,
        }

    async def run_scheduler(self):
        self.running = True
        while self.running:
            current_time = datetime.now()

            for job_name, job in self.jobs.items():
                last_run = job["last_run"]

                if last_run is None or (
                    current_time - last_run
                ).total_seconds() >= job["interval"]:
                    try:
                        if asyncio.iscoroutinefunction(job["func"]):
                            await job["func"]()
                        else:
                            job["func"]()

                        job["last_run"] = current_time
                        job["run_count"] += 1
                    except Exception as e:
                        print(f"Job {job_name} failed: {e}")

            await asyncio.sleep(1)

    def stop_scheduler(self):
        self.running = False

    def get_job_status(self) -> dict:
        return {
            job_name: {
                "interval": job["interval"],
                "last_run": job["last_run"].isoformat() if job["last_run"] else None,
                "run_count": job["run_count"],
            }
            for job_name, job in self.jobs.items()
        }


global_task_queue = TaskQueue(max_queue_size=1000, workers=5)
global_scheduler = BackgroundJobScheduler()
