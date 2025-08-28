"""Patent ingest worker for processing XML and PDF patent documents."""

from .worker import PatentIngestWorker

__all__ = ["PatentIngestWorker"]
