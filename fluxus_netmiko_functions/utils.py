import json
import os
from fluxus_sdk.logger import logger


def write_to_file(file_path, data):
    """Write data to a file."""
    logger.debug(f"Writing data to {file_path}")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as file:
        file.write(data)


def write_json_to_file(file_path, data):
    """Write JSON data to a file."""
    logger.debug(f"Writing JSON data to {file_path}")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)


def log_nornir_sub_exception(exception):
    exception = exception.result[-1].exception
    logger.error(exception)
    raise exception
