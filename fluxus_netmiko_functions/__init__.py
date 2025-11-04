from fluxus_netmiko_functions.tasks.collect_device_config import (
    collect_device_configuration,
)
from fluxus_netmiko_functions.tasks.collect_stateful_commands import (
    collect_stateful_commands,
)
from fluxus_netmiko_functions.tasks.run_commands import run_command


__fluxus__ = [
    collect_device_configuration,
    collect_stateful_commands,
    run_command,
]
