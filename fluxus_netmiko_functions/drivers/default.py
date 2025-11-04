"""Default collection of Nornir Tasks based on Napalm."""

import logging
import os
import time

from netmiko import NetmikoAuthenticationException, NetmikoTimeoutException
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task
from nornir_netmiko.tasks import netmiko_send_command, netmiko_send_config

from opti_network_automation.exceptions import OptiNetworkAutomationException
from opti_network_automation.utils.logger import log_nornir_sub_exception


logger = logging.getLogger("opti_network_automation")


RUN_COMMAND_MAPPING = {
    "default": "show run",
    "arista_eos": "show run",
    "cisco_aireos": "show run-config commands",
    "cisco_nxos": "show run",
    "cisco_ios": "show run",
    "cisco_wlc": "show running-config",
    "cisco_xr": "show run",
    "juniper_junos": "show configuration | display set",
    "netscaler": "show run",
}


class NetboxNornirDriver:
    """Default collection of Nornir Tasks based on Netmiko."""

    @staticmethod
    def get_config(task: Task) -> Result:
        """Get the latest configuration from the device using Netmiko.

        Args:
            task (Task): Nornir Task.
            logger (NornirLogger): Custom NornirLogger object to reflect job results (via Netbox Jobs) and Python logger.
            obj (Device): A Netbox Device Django ORM object instance.
            remove_lines (list): A list of regex lines to remove configurations.
            substitute_lines (list): A list of dictionaries with to remove and replace lines.

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        logger.debug(
            f"Executing get_config for {task.host.name} on {task.host.platform}",
        )
        command = RUN_COMMAND_MAPPING.get(task.host.platform, RUN_COMMAND_MAPPING["default"])

        try:
            result = task.run(task=netmiko_send_command, command_string=command)
        except NornirSubTaskError as exc:
            if isinstance(exc.result.exception, NetmikoAuthenticationException):
                logger.error(
                    f"Failed with an authentication issue: `{exc.result.exception}`",
                )
                raise OptiNetworkAutomationException(
                    f"Failed with an authentication issue: `{exc.result.exception}`"
                ) from exc

            if isinstance(exc.result.exception, NetmikoTimeoutException):
                logger.error(
                    f"Failed with a timeout issue. `{exc.result.exception}`",
                )
                raise OptiNetworkAutomationException(f"Failed with a timeout issue. `{exc.result.exception}`") from exc

            for line in exc.result.result.splitlines():
                print(line)
            logger.error(
                f"Failed with an unknown issue. `{exc.result.exception}`",
            )
            raise OptiNetworkAutomationException(f"Failed with an unknown issue. `{exc.result.exception}`") from exc

        if result[0].failed:
            return result

        running_config = result[0].result

        # Primarily seen in Cisco devices.
        if "ERROR: % Invalid input detected at" in running_config:
            logger.error(
                "Discovered `ERROR: % Invalid input detected at` in the output",
            )
            raise OptiNetworkAutomationException("Discovered `ERROR: % Invalid input detected at` in the output")

        return Result(host=task.host, result={"config": running_config})

    @staticmethod
    def deploy_config(task: Task, config: str) -> Result:
        """Deploy the configuration to the device using Netmiko.

        Args:
            task (Task): Nornir Task.
            config (str): Configuration to deploy to the device.

        Returns:
            Result: Nornir Result object with a dict as a result containing the status of the deployment
                { "status: <True/False>", "error": <None/str> }
        """
        logger.debug(
            f"Executing deploy_configuration for {task.host.name} on {task.host.platform}",
        )

        # Split the config string into a list of commands
        config_commands = config.splitlines()

        try:
            task.run(
                task=netmiko_send_config,
                config_commands=config_commands,
            )
        except NornirSubTaskError as exc:
            if isinstance(exc.result.exception, NetmikoAuthenticationException):
                logger.error(
                    f"Failed with an authentication issue: `{exc.result.exception}`",
                )
                return Result(host=task.host, result={"status": False, "error": str(exc.result.exception)})

            if isinstance(exc.result.exception, NetmikoTimeoutException):
                logger.error(
                    f"Failed with a timeout issue. `{exc.result.exception}`",
                )
                return Result(host=task.host, result={"status": False, "error": str(exc.result.exception)})

            for line in exc.result.result.splitlines():
                print(line)
            logger.error(
                f"Failed with an unknown issue. `{exc.result.exception}`",
            )
            return Result(host=task.host, result={"status": False, "error": str(exc.result.exception)})

        return Result(host=task.host, result={"status": True, "error": None})

    @staticmethod
    def wait_until_reachable(task: Task, timeout: int = 30) -> Result:
        """Wait until the device is reachable.

        Args:
            task (Task): Nornir Task.
            timeout (int): Timeout in seconds to wait for the device to become reachable.

        Returns:
            Result: Nornir Result object with a dict as a result containing the status of the reachability
                { "status": <True/False> }
        """
        logger.debug(
            f"Executing wait_until_reachable for {task.host.name} on {task.host.platform}",
        )
        start_time = time.time()
        while start_time + timeout > time.time():
            response = os.system(f"ping -c 1 {task.host.hostname}")
            if response == 0:
                logger.info(f"{task.host.name} is reachable.")
                return Result(host=task.host, result={"status": True})
            else:
                logger.warning(f"{task.host.name} is not reachable, retrying...")
                time.sleep(1)
        logger.error(f"{task.host.name} is not reachable after {timeout} seconds.")
        return Result(host=task.host, result={"status": False})

    @staticmethod
    def reload_device(task: Task) -> Result:
        """Reload the device.

        Args:
            task (Task): Nornir Task.

        Returns:
            Result: Nornir Result object with a dict as a result containing:
                {
                    "status": <True/False>,
                    "error": <None or str>,
                    "output": <str from reload command> (optional)
                }
        """
        host_name = task.host.name
        platform = task.host.platform
        logger.debug(f"Starting reload for {host_name} (platform={platform})")

        try:
            # Send the “reload” command and wait for the “Proceed with reload” prompt
            r1 = task.run(
                task=netmiko_send_command,
                command_string="reload",
                expect_string=r"Proceed with reload",
            )
            output_reload = r1.result
            logger.debug(f"[{host_name}] reload prompt output:\n{output_reload}")

            # Send “confirm” to actually kick off the reload
            r2 = task.run(
                task=netmiko_send_command,
                command_string="confirm",
            )
            output_confirm = r2.result
            logger.debug(f"[{host_name}] confirm output:\n{output_confirm}")

            return Result(
                host=task.host,
                result={
                    "status": True,
                    "error": None,
                    "output": output_reload + "\n" + output_confirm,
                },
            )

        except NornirSubTaskError as e:
            err_msg = str(e)
            logger.error(f"Reload failed on {host_name} (NornirSubTaskError): {err_msg}")
            log_nornir_sub_exception(logger, e)
            return Result(
                host=task.host,
                result={"status": False, "error": err_msg},
            )

        except Exception as e:
            # Catch‐all for anything unexpected
            err_msg = str(e)
            logger.error(f"Reload failed on {host_name} (Unexpected): {err_msg}")
            log_nornir_sub_exception(logger, e)
            return Result(
                host=task.host,
                result={"status": False, "error": err_msg},
            )
