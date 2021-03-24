"""
Configuration management.  Basic approach is similar to
https://tech.preferred.jp/en/blog/working-with-configuration-in-python/
"""

import argparse
import datetime
import logging
import pathlib
import sys
import typing
from dataclasses import dataclass, field
from enum import Enum

import dacite
import yaml

_logger = logging.getLogger(__name__)


from ansto_radon_monitor import __version__

LogLevel = typing.NewType("LogLevel", int)


DETECTOR_KIND_CHOICES = ["L100", "L200", "L1500", "L5000"]

DetectorKind = typing.NewType("DetectorKind", str)


def parse_detector_kind(s: DetectorKind):
    s = s.upper()
    if not s in DETECTOR_KIND_CHOICES:
        raise RuntimeError(f"Unknown kind of radon detector: {s}")
    return s


@dataclass
class DetectorConfig:
    """
    Configuration of a single radon detector
    """

    name: str = ""
    serial_port: str = ""
    detector_kind: str = ""


@dataclass
class Configuration:
    """
    Configuration of the entire app
    """

    number_of_detectors: int = 1
    number_of_calibration_units: int = 1
    loglevel: LogLevel = LogLevel(logging.WARN)
    pid_file: pathlib.Path = pathlib.Path("/tmp/ansto_radon_monitor.pid")
    detector_config: typing.List[DetectorConfig] = field(default_factory=list)
    data_dir: pathlib.Path = pathlib.Path(".", "data").absolute()
    labjack_id: int = -1


def parse_config(raw_cfg):
    # define converters/validators for the various data types we use
    # a dict mapping a type to a convertor function
    converters = {
        pathlib.Path: lambda x: pathlib.Path(x).absolute(),
        int: int,
        LogLevel: lambda x: LogLevel(logging._nameToLevel[x]),
        DetectorKind: parse_detector_kind,
    }

    # create and validate the Configuration object
    configuration = dacite.from_dict(
        data_class=Configuration,
        data=raw_cfg,
        config=dacite.Config(type_hooks=converters),
    )

    return configuration


def get_parser():
    parser = argparse.ArgumentParser(
        description="Control and monitoring for ANSTO radon detectors"
    )

    parser.add_argument(
        "-c",
        "--config",
        type=lambda p: pathlib.Path(p).absolute(),
        default=pathlib.Path(pathlib.Path(".").absolute(), "config.yaml"),
        help="Name of configuration file",
        dest="configuration_file",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="ansto_radon_monitor {ver}".format(ver=__version__),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const="INFO",
    )
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const="DEBUG",
    )

    parser.add_argument(
        "action", choices=["run", "query"], default="run", help="action to perform",
    )
    return parser


def parse_args(args: typing.List[str]):
    """Parse command line parameters

    Args:
        args ([str]): command line parameters as list of strings

    Returns:
        :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = get_parser()
    return parser.parse_args(args)


def config_from_commandline(
    args: typing.List[str], raw_cfg: typing.Union[dict, None] = None
):
    """Load the application configuration, based on command line options

    Parameters
    ----------
    args : list[str]
        command line arguments
    
    raw_cfg : dict, optional
        raw configuration, optional.  If present, then `raw_cfg` is used instead of reading from
        a configuration file.
    """

    cmdline_args = parse_args(args)

    if raw_cfg is None:
        if cmdline_args.configuration_file.exists():
            with open(cmdline_args.configuration_file, "rt") as fd:
                raw_cfg = yaml.safe_load(fd.read())
        else:
            _logger.error(
                f'Configuration file "{cmdline_args.configuration_file}" does not exist.'
            )
            get_parser().print_help(sys.stderr)
            sys.exit(1)

    # over-write config where options have been specified on the command line
    for k in ["loglevel"]:
        val = vars(cmdline_args)[k]
        if val is not None:
            raw_cfg[k] = val

    config = parse_config(raw_cfg)

    # validate configuration
    # (doing this early seems helpful, but may not be ideal in some respects.
    # Consider moving it later, e.g. when DataStore is initialized)
    # if not config.data_dir.exists():
    #    _logger.error(f'Data storage directory "{config.data_dir}" does not exist.')

    # TODO: get logging working from this function
    print(f"Configuration parsed: {config}")
    _logger.debug(f"Configuration parsed: {config}")

    return config


def config_from_yamlfile(filename):
    with open(filename, "rt") as fd:
        raw_cfg = yaml.safe_load(fd.read())
    config = parse_config(raw_cfg)
    return config


if __name__ == "__main__":
    raw_cfg = raw_cfg = {
        "detector_config": [
            {"kind": "L1500", "name": "low", "port": "/dev/ttyS0"},
            {"kind": "L1500", "name": "high", "port": "/dev/ttyS1"},
        ],
        "number_of_detectors": "2",
        "loglevel": "ERROR",
    }
    configuration = parse_config(raw_cfg)

    import pprint

    pprint.pprint(configuration)

    args = ["-vv", "--config=test.yaml"]
    print(parse_args(args))

    args = ["-vv", "--config=__USE_DUMMY_INTERNAL_CONFIG"]
    config = config_from_commandline(args)
    assert config.loglevel == logging.DEBUG

    args = ["--config=__USE_DUMMY_INTERNAL_CONFIG"]
    config = config_from_commandline(args)
    assert config.loglevel == logging.ERROR
