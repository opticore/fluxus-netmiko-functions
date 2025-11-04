"""This module contains tasks for network state management.

"""

import logging
import json
import os
from datetime import datetime

from opti_network_automation import app_config
from opti_network_automation.config_management.state.nornir_tasks import (
    get_device_state,
)
from opti_network_automation.connectivity.init_nornir import init_nornir
from opti_network_automation.utils.file_management import write_to_file, write_json_to_file


logger = logging.getLogger(__name__)


__all__ = [
    "collect_state",
]


def collect_state(output, output_folder, nornir=None):
    """Collect the state of network devices.

    Args:
        output (bool): Whether to write output to a file.
        output_folder (str, optional): Folder to save output files.
    """
    if not nornir:
        nornir = init_nornir()

    logger.info(f"Starting state collection...")
    results = nornir.run(task=get_device_state)
    logger.info("Result of state collection:")
    timestamp = datetime.now().strftime(app_config.SETTINGS.workspace.timestamp)

    if output_folder:
        base_path = output_folder
    else:
        base_path = os.path.join(app_config.SETTINGS.workspace.path, "snapshots", timestamp)

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
                            base_path,
                            "state",
                            host,
                            f"{host}__{command['cmd'].replace(' ', '_')}.json",
                        ),
                        command["structured"],
                    )
                if command["unstructured"]:
                    write_to_file(
                        os.path.join(
                            base_path,
                            "state",
                            host,
                            f"{host}__{command['cmd'].replace(' ', '_')}.output",
                        ),
                        command["unstructured"],
                    )
    logger.info("State collection finished!")
