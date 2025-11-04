import json
import os
import traceback

from nornir_netmiko import netmiko_send_command
from nornir.core import Nornir
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Task, Result
from datetime import datetime
from typing import Annotated

from fluxus_netmiko_functions.textfsm import get_state_textfsm
from fluxus_netmikto_functions.utils import write_to_file, write_json_to_file

from fluxus_sdk.logger import logger
from fluxus_sdk.func import fluxus_func


def process_structured_output(structured_data, ignore_columns=[]):
    if isinstance(structured_data, list):
        for item in structured_data:
            for key in ignore_columns:
                if key in item:
                    item[f"__{key}"] = item.pop(key)

    elif isinstance(structured_data, dict):
        for key in ignore_columns:
            if key in structured_data:
                structured_data[f"__{key}"] = structured_data.pop(key)

    return structured_data


def get_device_state(task: Task) -> Result:
    """
    Collects the state of a network device.

    This function runs specified commands on a network device and retrieves
    both unstructured and structured results.

    Args:
        task (Task): A Nornir task instance.

    Returns:
        Result: A Nornir Result object containing the command outputs and additional info.
    """
    try:
        results = []
        platform = task.host.data.get("platform", "")
        if type(platform) is dict:
            platform = platform.get("slug", "")

        commands = task.host.data.get("commands", [])
        if not commands:
            commands = task.host.data.get("config_context", {}).get("commands", [])

        for cmd in commands:
            logger.info(f"[{task.host.name}] Running command: {cmd}")
            try:
                unstructured_result = task.run(
                    task=netmiko_send_command, command_string=cmd["command"]
                )
                structured_result = get_state_textfsm(
                    platform, cmd["command"], unstructured_result[0].result
                )
                structured_result = process_structured_output(
                    structured_result, ignore_columns=cmd.get("ignore_columns", [])
                )
                logger.debug(
                    f"[{task.host.name}] Structured result: {structured_result}"
                )
                logger.debug(
                    f"[{task.host.name}] Unstructured result: {unstructured_result[0].result}"
                )

                result = {
                    "cmd": cmd["command"],
                    "structured": structured_result if structured_result else None,
                    "unstructured": (
                        unstructured_result[0].result
                        if not unstructured_result[0].failed
                        else None
                    ),
                }
                results.append(result)
            except Exception as inner_error:
                logger.error(f"[{task.host.name}] State collection failed")
                for line in traceback.format_exc().splitlines():
                    logger.error(line)
                return Result(
                    host=task.host, result={"status": False, "error": inner_error}
                )

        logger.info(f"[{task.host.name}] State collection successful")
        return Result(host=task.host, result=json.dumps(results))

    except NornirSubTaskError as error:
        logger.error(f"[{task.host.name}] Nornir SubTask Error: {error}")
        return Result(host=task.host, result={"status": False, "error": str(error)})
    except Exception as error:
        logger.error(f"[{task.host.name}] Unexpected error occurred: {error}")
        traceback.print_exc()
        return Result(host=task.host, result={"status": False, "error": str(error)})


@fluxus_func(
    name="collect_stateful_commands",
    description="Collect the state of network devices.",
    dir_path="netmiko/",
)
def collect_stateful_commands(
    nornir: Nornir,
    output: Annotated[bool, "Whether to write output to a file."] = False,
    output_folder: Annotated[str, "Folder to save output files."] = "",
):
    """Collect the state of network devices.

    Args:
        output (bool): Whether to write output to a file.
        output_folder (str, optional): Folder to save output files.
    """

    logger.info(f"Starting state collection...")
    results = nornir.run(task=get_device_state)
    logger.info("Result of state collection:")

    for host in results:
        result = results[host][0].result
        if type(result) is str:
            result = json.loads(result)
        if output:
            for command in result:
                logger.info(command)
                if command["structured"]:
                    write_json_to_file(
                        os.path.join(
                            output_folder,
                            "state",
                            host,
                            f"{host}__{command['cmd'].replace(' ', '_')}.json",
                        ),
                        command["structured"],
                    )
                if command["unstructured"]:
                    write_to_file(
                        os.path.join(
                            output_folder,
                            "state",
                            host,
                            f"{host}__{command['cmd'].replace(' ', '_')}.output",
                        ),
                        command["unstructured"],
                    )
    logger.info("State collection finished!")
