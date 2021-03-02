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
import sys
import time

from ansto_radon_monitor import __version__
from ansto_radon_monitor.configuration import Configuration, config_from_commandline
from ansto_radon_monitor.datastore import DataStore
from ansto_radon_monitor.main_controller import MainController, initialize

__author__ = "Alan Griffiths"
__copyright__ = "Alan Griffiths"
__license__ = "mit"

_logger = logging.getLogger(__name__)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
        loglevel (int): minimum loglevel for emitting messages
    """
    # logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logformat = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d %(threadName)s] %(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )


def main(args):
    """Main entry point allowing external calls

    Args:
        args ([str]): command line parameter list
    """
    # inital logging setup so that we can see messages from config parser
    setup_logging(logging.DEBUG)
    configuration = config_from_commandline(args)
    setup_logging(configuration.loglevel)
    _logger.debug("Setting up...")
    try:
        control = initialize(configuration, mode="thread")
        time.sleep(30)

        print(control.datastore.data)

        control.shutdown()

    finally:
        _logger.debug("Main function exiting.")


def run():
    """Entry point for console_scripts"""
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
