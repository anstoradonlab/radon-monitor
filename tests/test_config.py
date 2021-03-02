# -*- coding: utf-8 -*-

import pytest

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
    assert config1.detector_config[0].kind == DetectorKind.L1500


def test_parse_command_line_args():
    args = ["-vv", "--config=test.yaml"]
    config = parse_args(args)
    assert config
    print(parse_args(args))


def test_load_config_from_commandline():
    args = ["-vv", "--config=__USE_DUMMY_INTERNAL_CONFIG"]
    config = config_from_commandline(args)
    assert config.loglevel == logging.DEBUG

    args = ["--config=__USE_DUMMY_INTERNAL_CONFIG"]
    config = config_from_commandline(args)
    assert config.loglevel == logging.ERROR
