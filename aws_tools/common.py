import os
import boto3
import logging


def get_logger(name: str | None = None) -> logging.Logger:
    log_level = logging.DEBUG if os.environ.get("DEBUG_MODE", "") else logging.INFO
    logging.basicConfig(
        format=r'%(levelname)s [%(asctime)s]: "%(message)s"',
        datefmt=r'%Y-%m-%d %H:%M:%S', level=log_level
    )
    return logging.getLogger(name)


class API:
    def __init__(self, type: str) -> None:
        self.client = boto3.client(type)
        self.items = []

    def load_items(self) -> None:
        raise NotImplementedError
