import logging
import logging.handlers
from queue import Queue

log_queue = Queue()

bastion_logger = logging.getLogger("pipeline")
bastion_logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()

formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s")
console_handler.setFormatter(formatter)

queue_handler = logging.handlers.QueueHandler(log_queue)

bastion_logger.addHandler(queue_handler)

listener = logging.handlers.QueueListener(log_queue, console_handler)
listener.start()
