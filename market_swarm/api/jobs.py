"""Job manager for async simulation execution.

In-memory registry with file-based persistence. Jobs are tracked in
results/_jobs.json, full results stored as results/{job_id}.json.
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..models import SimulationResult
from .models import JobResponse, JobStatus, ProgressInfo


class Job:
    """Internal job state — not exposed directly via API."""

    __slots__ = (
        "id",
        "status",
        "product_yaml",
        "product_name",
        "pack_type",
        "model_name",
        "created_at",
        "started_at",
        "completed_at",
        "error",
        "progress_completed",
        "progress_total",
    )

    def __init__(
        self,
        product_yaml: str,
        product_name: str,
        pack_type: str,
        model_name: str,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.status = JobStatus.pending
        self.product_yaml = product_yaml
        self.product_name = product_name
        self.pack_type = pack_type
        self.model_name = model_name
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.progress_completed = 0
        self.progress_total = 0

    def to_response(self) -> JobResponse:
        return JobResponse(
            job_id=self.id,
            status=self.status,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            product_name=self.product_name,
            pack_type=self.pack_type,
            model_name=self.model_name,
            progress=ProgressInfo(
                completed=self.progress_completed,
                total=self.progress_total,
            ),
            error=self.error,
        )

    def to_index_dict(self) -> dict:
        """Minimal dict for _jobs.json index."""
        return {
            "id": self.id,
            "status": self.status.value,
            "product_name": self.product_name,
            "pack_type": self.pack_type,
            "model_name": self.model_name,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }

    @classmethod
    def from_index_dict(cls, data: dict) -> "Job":
        job = cls.__new__(cls)
        job.id = data["id"]
        job.status = JobStatus(data["status"])
        job.product_yaml = ""  # Not stored in index
        job.product_name = data["product_name"]
        job.pack_type = data["pack_type"]
        job.model_name = data["model_name"]
        job.created_at = datetime.fromisoformat(data["created_at"])
        job.started_at = (
            datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        )
        job.completed_at = (
            datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )
        job.error = data.get("error")
        job.progress_completed = 0
        job.progress_total = 0
        return job


class JobManager:
    """Thread-safe job registry with file-based persistence."""

    def __init__(self, storage_dir: str | Path = "results") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._load_index()

    def _index_path(self) -> Path:
        return self.storage_dir / "_jobs.json"

    def _result_path(self, job_id: str) -> Path:
        return self.storage_dir / f"{job_id}.json"

    def _load_index(self) -> None:
        """Load job index from disk on startup."""
        index_file = self._index_path()
        if not index_file.exists():
            return
        try:
            data = json.loads(index_file.read_text())
            for entry in data:
                job = Job.from_index_dict(entry)
                # Mark incomplete jobs as failed (server restarted)
                if job.status in (JobStatus.pending, JobStatus.running):
                    job.status = JobStatus.failed
                    job.error = "Server restarted during execution"
                self._jobs[job.id] = job
        except (json.JSONDecodeError, KeyError):
            pass  # Corrupted index — start fresh

    def _save_index(self) -> None:
        """Persist job index to disk."""
        entries = [job.to_index_dict() for job in self._jobs.values()]
        self._index_path().write_text(json.dumps(entries, indent=2, ensure_ascii=False))

    def create_job(
        self,
        product_yaml: str,
        product_name: str,
        pack_type: str,
        model_name: str,
    ) -> Job:
        job = Job(
            product_yaml=product_yaml,
            product_name=product_name,
            pack_type=pack_type,
            model_name=model_name,
        )
        with self._lock:
            self._jobs[job.id] = job
            self._save_index()
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def mark_running(self, job_id: str, total_personas: int) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.running
                job.started_at = datetime.now(timezone.utc)
                job.progress_total = total_personas
                self._save_index()

    def update_progress(self, job_id: str, completed: int) -> None:
        job = self._jobs.get(job_id)
        if job:
            job.progress_completed = completed

    def mark_completed(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.completed
                job.completed_at = datetime.now(timezone.utc)
                self._save_index()

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.failed
                job.completed_at = datetime.now(timezone.utc)
                job.error = error
                self._save_index()

    def save_result(self, job_id: str, result: SimulationResult) -> None:
        """Write full result to disk as JSON."""
        result_data = result.model_dump()
        result_data["_meta"] = {
            "job_id": job_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        self._result_path(job_id).write_text(
            json.dumps(result_data, indent=2, ensure_ascii=False, default=str)
        )

    def load_result(self, job_id: str) -> Optional[dict]:
        """Load result from disk."""
        path = self._result_path(job_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None
