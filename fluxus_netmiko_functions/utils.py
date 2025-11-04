import os
from fluxus_sdk.logger import logger


def write_to_file(file_path, data):
    """Write data to a file."""
    logger.debug(f"Writing data to {file_path}")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as file:
        file.write(data)


def log_nornir_sub_exception(logger, exception):
    exception = exception.result[-1].exception
    logger.error(exception)
    raise exception
