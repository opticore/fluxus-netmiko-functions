import os
import traceback

from datetime import datetime
from nornir.core import Nornir
from nornir.core.task import Task, Result
from nornir.core.exceptions import NornirSubTaskError
from typing import Annotated

from fluxus_sdk.logger import logger
from fluxus_sdk.func import fluxus_func

from fluxus_netmiko_functions.dispatcher import dispatcher
from fluxus_netmiko_functions.utils import log_nornir_sub_exception, write_to_file


def sub_collect_device_configuration(task: Task) -> Result:
    try:
        get_config_task = task.run(
            task=dispatcher,
            name="Get Configuration",
            method="get_config",
        )[1]
        if get_config_task.result.get("config"):
            logger.info(f"[{task.host.name}] Configuration collection successful")
            logger.debug(
                f"[{task.host.name}] Configuration: \n"
                + get_config_task.result["config"]
            )
            return Result(
                host=task.host,
                result={
                    "status": True,
                    "error": None,
                    "config": get_config_task.result["config"],
                },
            )
        else:
            logger.error(f"[{task.host.name}] Configuration collection failed")
            return Result(
                host=task.host,
                result={"status": False, "error": get_config_task.result["error"]},
            )
    except NornirSubTaskError as error:
        log_nornir_sub_exception(error)
        return Result(host=task.host, result={"status": False, "error": str(error)})
    except Exception as error:
        logger.error(f"[{task.host.name}] Configuration collection failed: {error}")

        for line in traceback.format_exc().splitlines():
            logger.error(line)
        return Result(host=task.host, result={"status": False, "error": str(error)})


@fluxus_func(
    name="collect_device_configuration",
    description="Collect the configuration of all devices in the network.",
    dir_path="netmiko/",
)
def collect_device_configuration(
    nornir: Annotated[Nornir, "The Nornir object."],
    output: Annotated[bool, "Whether to write the configuration to a file."] = False,
    output_path: Annotated[str, "The path to write the configuration to."] = "",
):
    """Collect the configuration of all devices in the network.

    Args:
        output (bool, optional): Whether to write the configuration to a file
        output_path (str, optional): The path to write the configuration to

    Returns:
        path (str): The path to the directory containing the configuration files
    """
    logger.info("Starting configuration collection...")
    result = nornir.run(task=sub_collect_device_configuration)
    logger.info("Result of configuration collection:")

    for host, task_result in result.items():
        if output:
            write_to_file(
                os.path.join(
                    output_path,
                    f"{host}.cfg",
                ),
                task_result.result["config"],
            )
            logger.info("Configuration collection finished!")
