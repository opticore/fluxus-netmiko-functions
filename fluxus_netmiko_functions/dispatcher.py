import importlib

from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task

from fluxus_sdk.logger import logger

from fluxus_netmiko_functions.exceptions import FluxusNetmikoException


_DEFAULT_DRIVERS_MAPPING = {
    "default": "fluxus_netmikto_functions.drivers.default.NetboxNornirDriver",
    "default_netmiko": "fluxus_netmikto_functions.drivers.default.NetmikoNetboxNornirDriver",
    "arista_eos": "fluxus_netmikto_functions.drivers.arista_eos.NetboxNornirDriver",
    "cisco_aireos": "fluxus_netmikto_functions.drivers.cisco_aireos.NetboxNornirDriver",
    "cisco_asa": "fluxus_netmikto_functions.drivers.cisco_asa.NetboxNornirDriver",
    "cisco_ios": "fluxus_netmikto_functions.drivers.cisco_ios.NetboxNornirDriver",
    "cisco_ios_restconf": "fluxus_netmikto_functions.drivers.cisco_ios_restconf.NetboxNornirDriver",
    "cisco_nxos": "fluxus_netmikto_functions.drivers.cisco_nxos.NetboxNornirDriver",
    "cisco_wlc": "fluxus_netmikto_functions.drivers.cisco_wlc.NetboxNornirDriver",
    "cisco_xr": "fluxus_netmikto_functions.drivers.cisco_ios_xr.NetboxNornirDriver",
    "fortinet_fortios": "fluxus_netmikto_functions.drivers.fortinet_fortios.NetboxNornirDriver",
    "juniper_junos": "fluxus_netmikto_functions.drivers.juniper_junos.NetboxNornirDriver",
    "netscaler": "fluxus_netmikto_functions.drivers.netscaler.NetboxNornirDriver",
    "paloalto_panos": "fluxus_netmikto_functions.drivers.paloalto_panos.NetboxNornirDriver",
}


def dispatcher(task: Task, method: str, *args, **kwargs) -> Result:
    """Helper Task to retrieve a given Nornir task for a given platform.

    Args:
        task (Nornir Task):  Nornir Task object.
        method (str):  The string value of the method to dynamically find.

    Returns:
        Result: Nornir Task result.
    """
    if kwargs.get("default_drivers_mapping"):
        default_drivers_mapping = kwargs["default_drivers_mapping"]
        del kwargs["default_drivers_mapping"]
    else:
        default_drivers_mapping = _DEFAULT_DRIVERS_MAPPING

    logger.debug(
        f"Executing dispatcher for {task.host.name} ({task.host.platform})",
    )

    # Get the platform specific driver, if not available, get the default driver
    driver = default_drivers_mapping.get(task.host.platform)
    if not driver:
        logger.error(
            f"Unable to find the driver for {method} for platform: {task.host.platform}, preemptively failed.",
        )
        raise FluxusNetmikoException(
            f"Unable to find the driver for {method} for platform: {task.host.platform}, preemptively failed."
        )

    logger.debug(f"Found driver {driver}")

    module_name, class_name = driver.rsplit(".", 1)
    driver_class = getattr(importlib.import_module(module_name), class_name)

    if not driver_class:
        logger.error(
            f"Unable to locate the class {driver}, preemptively failed.",
        )
        raise FluxusNetmikoException(
            f"Unable to locate the class {driver}, preemptively failed."
        )

    try:
        driver_task = getattr(driver_class, method)
    except AttributeError:
        logger.error(
            f"Unable to locate the method {method} for {driver}, preemptively failed.",
        )
        raise FluxusNetmikoException(
            f"Unable to locate the method {method} for {driver}, preemptively failed."
        )

    result = None
    error = None
    try:
        result = task.run(task=driver_task, *args, **kwargs)
    except NornirSubTaskError as exc:
        traceback_lines = exc.result[0].result.splitlines()
        # logger.error(f"Subtask failed: {traceback_lines[-1]}")
        # error = traceback_lines[-1]
        # for line in traceback_lines:
        #     logger.debug(line)
        raise FluxusNetmikoException(f"Subtask failed: {traceback_lines[-1]}")
    return Result(
        host=task.host,
        result=result,
        error=error,
    )
