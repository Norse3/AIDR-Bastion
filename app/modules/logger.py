import logging
import logging.handlers
from queue import Queue

from settings import get_settings

settings = get_settings()

log_queue = Queue()

bastion_logger = logging.getLogger(settings.PROJECT_NAME)
bastion_logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()

formatter = logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s]%(message)s")
console_handler.setFormatter(formatter)

queue_handler = logging.handlers.QueueHandler(log_queue)

bastion_logger.addHandler(queue_handler)

listener = logging.handlers.QueueListener(log_queue, console_handler)
listener.start()
