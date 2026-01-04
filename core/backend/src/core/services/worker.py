from arq import ArqRedis

from core.infrastructure.logging import get_logger
from core.services.base import BaseService

logger = get_logger(__name__)


class WorkerService(BaseService):
    """Service for handling worker-related functionality"""

    def __init__(self, arq: ArqRedis, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.arq = arq

    async def enqueue_job(self, job_name: str, *args, **kwargs):
        """Enqueue a job to be processed by the worker"""
        job = await self.arq.enqueue_job(job_name, *args, **kwargs)
        logger.info(f"Enqueued job {job_name} with ID {job.job_id}")
        return job
