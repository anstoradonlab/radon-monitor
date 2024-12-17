# -*- coding: utf-8 -*-
"""
This is a skeleton file that can serve as a starting point for a Python
console script. To run this script uncomment the following lines in the
[options.entry_points] section in setup.cfg:

    console_scripts =
         fibonacci = ansto_radon_monitor.skeleton:run

Then run `python setup.py install` which will install the command `fibonacci`
inside your current environment.
Besides console scripts, the header (i.e. until _logger...) of this file can
also be used as template for Python modules.

Note: This skeleton file can be safely removed if not needed!
"""

import argparse
import logging
import os
import sys
import time

from ansto_radon_monitor import __version__
from ansto_radon_monitor.configuration import (Configuration,
                                               config_from_commandline,
                                               parse_args,
                                               setup_logging)
from ansto_radon_monitor.datastore import DataStore
from ansto_radon_monitor.main_controller import MainController, initialize

__author__ = "Alan Griffiths"
__copyright__ = "Alan Griffiths"
__license__ = "mit"

_logger = logging.getLogger(__name__)


def main(args):
    """Main entry point allowing external calls

    Args:
        args ([str]): command line parameter list
    """
    # auxillary functions

    # these do not require a config file, so parse the command line args early
    if len(args) == 0 and os.name == "nt":
        # start gui - late import because gui libraries may not be installed
        from ansto_radon_monitor.gui.main import main as guimain
        guimain()
        return
    # on linux, gui is started from a commandline action
    cmdline_args = parse_args(args)
    if cmdline_args.action == "gui":
        from ansto_radon_monitor.gui.main import main as guimain
        guimain()
        return
    
    if cmdline_args.action == "listserialports":
        import serial.tools.list_ports

        n = 0
        for info in sorted(serial.tools.list_ports.comports()):
            print(
                f"{info.device}\n    description: {info.description}\n           hwid: {info.hwid}"
            )
            n += 1
        if n == 1:
            print(f"{n} port found")
        else:
            print(f"{n} ports found")
        return

    if cmdline_args.action == "listlabjacks":
        from .labjack_interface import list_all_u12

        info = list_all_u12()
        # info: {'serialnumList': <u12.c_long_Array_127 object at 0x00E2AD50>,
        #       'numberFound': 1, '
        #        localIDList': <u12.c_long_Array_127 object at 0x00E2Au12.DA0>}
        try:
            n = len(info["localIDList"])
        except IndexError:
            n = 0
        for ii in range(n):
            print(
                f"Labjack\n    local ID: {info['localIDList'][ii]}\n      serial: {info['serialnumList'][ii]}"
            )
        if n == 1:
            print(f"{n} LabJack found")
        else:
            print(f"{n} LabJacks found")
        return

    # inital logging setup so that we can see messages from config parser
    setup_logging(logging.DEBUG)
    configuration, cmdline_args = config_from_commandline(args)
    setup_logging(configuration.loglevel, log_pakbus_activity=configuration.log_pakbus_activity)
    _logger.debug("Setting up...")

    if cmdline_args.action == "run":
        if configuration.foreground:
            mode = "foreground"
        else:
            mode = "daemon"
        control = initialize(configuration, mode=mode)
        return

    # other actions mean that we need to connect
    try:
        control = initialize(configuration, mode="connect")
    except zerorpc.exceptions.LostRemote:
        print("Unable to connect to a running background process.")
        control = None

    if cmdline_args.action == "quit":
        if control is None:
            return
        control.terminate()

    elif cmdline_args.action == "query":
        print("Current status:")
        import pprint

        pprint.pprint(control.get_status())

    elif cmdline_args.action == "calibrate":
        control.run_calibration()
    else:
        raise NotImplementedError(
            f"Command line action '{cmdline_args.action}' not implemented"
        )


def run():
    """Entry point for console_scripts"""
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
