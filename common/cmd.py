import sys
import json
from dolfin import MPI, mpi_comm_world


RED = "\033[1;37;31m{s}\033[0m"
BLUE = "\033[1;37;34m{s}\033[0m"
GREEN = "\033[1;37;32m{s}\033[0m"
YELLOW = "\033[1;37;33m{s}\033[0m"
CYAN = "\033[1;37;36m{s}\033[0m"
NORMAL = "{s}"
ON_RED = "\033[41m{s}\033[0m"


# Stolen from Oasis
def convert(data):
    if isinstance(data, dict):
        return {convert(key): convert(value)
                for key, value in data.iteritems()}
    elif isinstance(data, list):
        return [convert(element) for element in data]
    elif isinstance(data, unicode):
        return data.encode('utf-8')
    else:
        return data


def parse_command_line():
    cmd_kwargs = dict()
    for s in sys.argv[1:]:
        if s.count('=') == 1:
            key, value = s.split('=', 1)
        elif s in ["-h", "--help", "help"]:
            key, value = "help", "true"
        else:
            raise TypeError("Only kwargs separated with '=' allowed.")
        try:
            value = json.loads(value)
        except ValueError:
            # json understands true/false, not True/False
            if value in ["True", "False"]:
                value = eval(value)
            elif "True" in value or "False" in value:
                value = eval(value)

        if isinstance(value, dict):
            value = convert(value)

        cmd_kwargs[key] = value
    return cmd_kwargs


def info_style(message, check=True, style=NORMAL):
    if MPI.rank(mpi_comm_world()) == 0 and check:
        print style.format(s=message)


def info_red(message, check=True):
    info_style(message, check, RED)


def info_blue(message, check=True):
    info_style(message, check, BLUE)


def info_yellow(message, check=True):
    info_style(message, check, YELLOW)


def info_green(message, check=True):
    info_style(message, check, GREEN)


def info_cyan(message, check=True):
    info_style(message, check, CYAN)


def info(message, check=True):
    info_style(message, check)


def info_on_red(message, check=True):
    info_style(message, check, ON_RED)
