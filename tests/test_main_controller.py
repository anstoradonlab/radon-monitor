# -*- coding: utf-8 -*-

# WARNING: this test needs the logger and labjack to be plugged in!

import logging
import pprint
import tempfile
import time
import sys
import os
import pathlib
import subprocess

import pytest
import yaml
import ansto_radon_monitor
from ansto_radon_monitor.configuration import (config_from_commandline,
                                               raw_config_from_inifile,
                                               parse_args, parse_config)
from ansto_radon_monitor.main_controller import MainController, initialize

__author__ = "Alan Griffiths"
__copyright__ = "Alan Griffiths"
__license__ = "mit"


import json

config_str = (
"""
[data]
data_dir=./data-one-mock-detector
data_file=./data-one-mock-detector/radon.db
loglevel=INFO
legacy_file_write_approx_radon=False

[detector1]
kind=mock
serial_port=serial:/dev/ttyUSB0
name=TEST
csv_file_pattern=csv/{NAME}{MONTH}{YEAR}.CSV
datalogger_serial=-1
report_pakbus_statistics=True

[detector2]
kind=mock
serial_port=serial:/dev/ttyUSB1
name=TEST
csv_file_pattern=csv/{NAME}{MONTH}{YEAR}.CSV
datalogger_serial=-1
report_pakbus_statistics=True


[calbox]
kind=mock
labjack_id=-1
labjack_serial=-1
flush_duration_sec=1
inject_duration_sec=1
background_duration_sec=1
"""
)


def test_main_controller_in_thread(tmp_path):
    #pytest.skip('skip for now')
    print("testing in {}".format(tmp_path))
    orig_dir = os.getcwd()
    os.chdir(tmp_path)
    inipath = tmp_path / "config.ini"
    ddir = tmp_path / "data-one-mock-detector"
    os.makedirs(ddir)
    with open(inipath, 'wt') as fd:
        fd.write(config_str)
    raw_cfg = raw_config_from_inifile(inipath)
    config, cmdline_args = config_from_commandline(["run"], raw_cfg)

    print("RAW:", raw_cfg)
    print("PROCESSED:", config)

    os.chdir(orig_dir)

    print("initializing...")
    ctl = initialize(config, mode="thread")
    print("init done.")
    time.sleep(1)
    pprint.pprint(ctl.get_status())

    time.sleep(1)

    ctl.run_calibration()

    time.sleep(1)

    pprint.pprint(ctl.get_status())

    ctl.stop_calibration()
    ctl.run_background()
    ctl.stop_background()
    ctl.shutdown()


def test_main_controller_in_separate_process(tmp_path):
    if sys.platform == "nt":
        pytest.skip("Separate process not supported on Windows")
    
        print("testing in {}".format(tmp_path))
    

    print("testing in {}".format(tmp_path))
    orig_dir = os.getcwd()
    os.chdir(tmp_path)
    inipath = tmp_path / "config.ini"
    ddir = tmp_path / "data-one-mock-detector"
    os.makedirs(ddir)
    with open(inipath, 'wt') as fd:
        fd.write(config_str)
    
    # This would be better as a fixture, see:
    # https://til.simonwillison.net/pytest/subprocess-server
    cmd = [sys.executable, 
           str(pathlib.Path(ansto_radon_monitor.__file__).parent / "main.py"),
           "-c",
           str(inipath),
           "run"]
    
    print("Running:", " ".join(cmd))
    server = subprocess.Popen(cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    time.sleep(5)
    raw_cfg = raw_config_from_inifile(inipath)
    #raw_cfg["pid_file"] = tmp_path / "ansto_radon_monitor.pid"
    config, cmdline_args = config_from_commandline(["run"], raw_cfg)

    print("RAW:", raw_cfg)
    print("PROCESSED:", config)

    os.chdir(orig_dir)

    print("initializing...")
    ctl = initialize(config, mode="connect")
    print("init done.")
    time.sleep(1)
    pprint.pprint(ctl.get_status())

    time.sleep(1)

    ctl.run_calibration()

    time.sleep(1)

    pprint.pprint(ctl.get_status())

    ctl.stop_calibration()
    ctl.run_background()
    ctl.stop_background()
    ctl.shutdown()

    time.sleep(2)
    server.terminate()