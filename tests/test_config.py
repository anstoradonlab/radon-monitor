# -*- coding: utf-8 -*-

import pytest
import logging

import json
from ansto_radon_monitor.configuration import (
    parse_config,
    parse_args,
    config_from_commandline,
    DetectorKind,
)


__author__ = "Alan Griffiths"
__copyright__ = "Alan Griffiths"
__license__ = "mit"


import json

raw_cfg = json.loads(
    """{
"number_of_detectors": "2",
"detector_config":  [ 
    {"name": "low", "port":"/dev/ttyS0", "kind":"L1500"}, 
    {"name": "high", "port":"/dev/ttyS1", "kind":"L1500"} ]
}"""
)


def test_parse_config():
    config1 = parse_config(raw_cfg)
    assert config1.number_of_detectors == 2
    assert config1.detector_config[0].kind == "L1500"


def test_parse_command_line_args():
    args = ["-vv", "--config=test.yaml", "run"]
    config = parse_args(args)
    assert config
    print(parse_args(args))


def test_load_config_from_commandline():
    args = ["-vv", "run"]
    config, cmdline_args = config_from_commandline(args, raw_cfg=raw_cfg)
    assert config.loglevel == logging.DEBUG

    args = ["run"]
    config, cmdline_args = config_from_commandline(args, raw_cfg=raw_cfg)
    assert config.loglevel == logging.ERROR


def test_fg_flag():
    args = ["-fg", "run"]
    config, cmdline_args = config_from_commandline(args, raw_cfg=raw_cfg)
    assert config.foreground == True

    cfg_check = {
        "number_of_detectors": "2",
        "detector_config": [
            {"name": "low", "port": "/dev/ttyS0", "kind": "L1500"},
            {"name": "high", "port": "/dev/ttyS1", "kind": "L1500"},
        ],
        "foreground": "False",
    }
    config = parse_config(cfg_check)
    assert config.foreground == False

    args = ["run"]
    config, cmdline_args = config_from_commandline(args, raw_cfg=raw_cfg)
    assert config.foreground == False
