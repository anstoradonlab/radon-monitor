# -*- coding: utf-8 -*-

# WARNING: this test needs the logger and labjack to be plugged in!

import pytest
import logging
import time
import yaml
import tempfile
import pprint
from ansto_radon_monitor.configuration import (
    parse_config,
    parse_args,
    config_from_commandline,
    DetectorKind,
)

from ansto_radon_monitor.main_controller import MainController, initialize


__author__ = "Alan Griffiths"
__copyright__ = "Alan Griffiths"
__license__ = "mit"


import json

raw_cfg = yaml.safe_load(
    """
detector_config:
    - detector_kind: "L1500"
      serial_port: "serial:/dev/ttyUSB0:115200"
      name: "TEST-002M"
"""
)


@pytest.fixture(scope="session")
def temp_directory():
    print("Creating temp dir")
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname

    print("removing temp dir")


def test_main_controller(temp_directory):
    print("testing in {}".format(temp_directory))
    config, cmdline_args = config_from_commandline(["run"], raw_cfg)
    print("initializing...")
    ctl = initialize(config, mode="thread")
    print("init done.")
    time.sleep(1)
    pprint.pprint(ctl.get_status())

    time.sleep(10)

    ctl.run_calibration()

    time.sleep(10)

    pprint.pprint(ctl.get_status())

    ctl.stop_calibration()
    ctl.run_background()
    ctl.stop_background()
    ctl.shutdown()