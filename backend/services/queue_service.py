from repositories.queue_repo import QueueRepository


class QueueService:
    def __init__(self, queue_repo: QueueRepository) -> None:
        self._queue_repo = queue_repo

