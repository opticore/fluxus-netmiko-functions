"""
This module provides functionalities for parsing network device command outputs using TextFSM templates.

It utilizes the 'ntc_templates.parse' module to convert unstructured command outputs from network devices
into structured data. This is particularly useful in network automation tasks where consistent data formats
are required for further processing or analysis.
"""

from ntc_templates.parse import parse_output


def get_state_textfsm(platform, command, data):
    """
    Parses the command output from a network device into structured data using TextFSM templates.

    This function takes the raw output from a network device command, and uses TextFSM templates
    based on the device platform and command to parse this output into a structured format.

    Args:
        platform (str): The platform type of the network device (e.g., 'cisco_ios', 'juniper_junos').
        command (str): The network command whose output is to be parsed (e.g., 'show ip interface brief').
        data (str): The raw string output from the network command.

    Returns:
        list: A list of dictionaries, where each dictionary represents structured data corresponding to a
        part of the command output. The keys of the dictionary are derived from the TextFSM template.
    """
    parsed_output = parse_output(platform=platform, command=command, data=data)
    return parsed_output
