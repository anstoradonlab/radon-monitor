# -*- coding: utf-8 -*-

import json
import logging
import tempfile

import pytest
from ansto_radon_monitor.configuration import (config_from_commandline,
                                               raw_config_from_inifile,
                                               parse_args, parse_config)

__author__ = "Alan Griffiths"
__copyright__ = "Alan Griffiths"
__license__ = "mit"

INIFILE = "../sample_config.ini"

@pytest.fixture(scope="session")
def temp_directory():
    print("Creating temp dir")
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname

    print("removing temp dir")


def test_load_inifile():
    raw_cfg = raw_config_from_inifile(INIFILE)
    assert raw_cfg is not None

def get_raw_cfg():
    """helper for other tests"""
    raw_cfg = raw_config_from_inifile(INIFILE)
    return raw_cfg

    

def test_parse_command_line_args():
    args = ["-vv", "--config=../sample_config.ini", "run"]
    config = parse_args(args)
    assert config
    print(parse_args(args))


def test_load_config_from_commandline():
    args = ["-vv", "run"]
    config, cmdline_args = config_from_commandline(args, raw_cfg=get_raw_cfg())
    assert config.loglevel == logging.DEBUG

    args = ["run"]
    config, cmdline_args = config_from_commandline(args, raw_cfg=get_raw_cfg())
    assert config.loglevel != logging.ERROR


def test_fg_flag():
    args = ["-fg", "run"]
    config, cmdline_args = config_from_commandline(args, raw_cfg=get_raw_cfg())
    assert config.foreground == True

    args = ["run"]
    config, cmdline_args = config_from_commandline(args, raw_cfg=get_raw_cfg())
    assert config.foreground == False
