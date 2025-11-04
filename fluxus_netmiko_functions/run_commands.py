from typing import Annotated

from nornir_netmiko.tasks import netmiko_send_command
from fluxus_sdk.logger import logger
from fluxus_sdk.func import fluxus_func

from fluxus_netmiko_functions.textfsm import get_state_textfsm


@fluxus_func(
    name="run_command",
    description="Run a command on a network device.",
    dir_path="netmiko/",
)
def run_command(
    command: Annotated[str, "The command to run."],
    use_textfsm: Annotated[bool, "Use textfsm to parse the output."] = False,
) -> Annotated[dict, "The output of the command."]:
    logger.info("Running command: %s", command)
    result = nornir.run(
        task=netmiko_send_command,
        command_string=command,
    )
    data = {}
    for host, task_result in result.items():
        if task_result[0].failed:
            logger.error("Failed to run command on %s: %s", host, task_result[0].result)
            data[host] = task_result[0].result
        else:
            logger.info("%s: %s", host, result[host][0].result)
            if use_textfsm:
                data[host] = get_state_textfsm(
                    nornir.inventory.hosts[host].platform,
                    command,
                    task_result[0].result,
                )
            else:
                data[host] = task_result[0].result
    return data
