"""
Configuration management.  Basic approach is similar to
https://tech.preferred.jp/en/blog/working-with-configuration-in-python/
"""

import argparse
import configparser
import copy
import datetime
import logging
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
import os
import pathlib
import pprint
import sys
import typing
from dataclasses import dataclass, field
from enum import Enum

import dacite
import yaml

_logger = logging.getLogger(__name__)


from ansto_radon_monitor import __version__

LogLevel = typing.NewType("LogLevel", int)

# TODO: consider using an enumeration for detector kind?
# DetectorKind = typing.NewType("DetectorKind", str)

# DETECTOR_KIND_CHOICES = [
#     DetectorKind("L100"),
#     DetectorKind("L200"),
#     DetectorKind("L1500"),
#     DetectorKind("L5000"),
# ]


# def parse_detector_kind(s: DetectorKind) -> DetectorKind:
#     sup = DetectorKind(s.upper())
#     if not sup in DETECTOR_KIND_CHOICES:
#         raise RuntimeError(f"Unknown kind of radon detector: {s}")
#     return sup


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise ValueError("Boolean value expected.")


@dataclass
class DetectorConfig:
    """
    Configuration of a single radon detector
    """

    name: str = ""
    serial_port: str = ""
    baudrate: int = 9600
    kind: str = ""
    volume_m3: typing.Optional[float] = None
    thoron_delay_volume_m3: typing.Optional[float] = None
    thoron_delay_number_of_tanks: typing.Optional[float] = None
    datalogger_serial: int = -1
    csv_file_pattern: typing.Optional[str] = None
    datalogger_time_offset: float = 0.0
    report_pakbus_statistics: bool = False
    check_ntp_sync: typing.Optional[bool] = None


@dataclass
class CalUnitConfig:
    """
    Configuration of a calibration unit
    """

    kind: str = ""
    labjack_id: typing.Optional[int] = -1
    labjack_serial: int = -1
    me43_ip_address: typing.Optional[str] = None
    flush_flow_rate: float = 0.5
    inject_flow_rate: float = 0.5
    flush_duration_sec: int = 3600 * 12
    inject_duration_sec: int = 3600 * 6
    background_duration_sec: int = 3600 * 24
    radon_source_activity_bq: typing.Optional[float] = None
    flow_sensor_polynomial: typing.List[float] = field(default_factory=lambda: [0.1025, -0.17965, 0.0669979])


@dataclass
class FtpConfig:
    """
    FTP backup configuration
    """

    server: typing.Optional[str] = None
    user: typing.Optional[str] = None
    passwd: typing.Optional[str] = None
    directory: typing.Optional[str] = None


@dataclass
class Configuration:
    """
    Configuration of the entire app
    """

    foreground: bool = False
    loglevel: LogLevel = LogLevel(logging.ERROR)
    logfile: typing.Optional[pathlib.Path] = None
    pid_file: pathlib.Path = pathlib.Path("/tmp/ansto_radon_monitor.pid")
    data_dir: pathlib.Path = pathlib.Path(".", "data").absolute()
    data_file: typing.Optional[pathlib.Path] = None
    legacy_file_timezone: float = 0
    legacy_file_write_approx_radon: bool = True
    backup_time_of_day: datetime.time = datetime.time(0,10)
    detectors: typing.List[DetectorConfig] = field(default_factory=list)
    calbox: CalUnitConfig = field(default_factory=CalUnitConfig)
    ftp: FtpConfig = field(default_factory=FtpConfig)
    udp_destination: typing.Optional[str] = None
    udp_port: int = 51520
    udp_multicast_interface: typing.Optional[str] = None
    ntp_server: typing.Optional[str] = None

    
    def as_text(self, include_sensitive=False) -> str:
        """Generate a text version of the configuration

        Args:
            include_sensitive (bool, optional): 
            If *true* then include potentially senstive information. Defaults to False.

        Returns:
            str: pretty-printed text version of the configuration
        """
        config = self
        if not include_sensitive:
            config = self.as_redacted_config()
        else:
            config = self
        return pprint.pformat(config)
    
    def as_redacted_config(self):
        """
        Return a copy of the configuration with sensitive information removed
        """
        config = copy.deepcopy(self)
        if config.ftp.server is not None:
            config.ftp.server = "XXXXXXXX"
        if config.ftp.user is not None:
            config.ftp.user = "XXXXXXXX"
        if config.ftp.passwd is not None:
            config.ftp.passwd = "XXXXXXXX"
        return config
        

def parse_config(raw_cfg) -> Configuration:
    # define converters/validators for the various data types we use
    # a dict mapping a type to a convertor function
    converters = {
        pathlib.Path: lambda x: pathlib.Path(x).absolute(),
        int: int,
        LogLevel: lambda x: LogLevel(logging._nameToLevel[x]),
        #        DetectorKind: parse_detector_kind,
        bool: str2bool,
        float: float,
        datetime.time: lambda x: datetime.datetime.strptime(x, '%H:%M').time(),
        typing.List[float]: lambda x: [float(itm) for itm in x.strip('[]').split(',')],
    }

    # create and validate the Configuration object
    configuration = dacite.from_dict(
        data_class=Configuration,
        data=raw_cfg,
        config=dacite.Config(type_hooks=converters),
    )

    # handle data_file not set (which is probably the usual case)
    if configuration.data_file is None:
        configuration.data_file = pathlib.Path(
            configuration.data_dir, "current", "radon.db"
        )
    
    # For the ntp server configuration, set the per-detector
    # flags if the user has set a ntp server address
    for detconfig in configuration.detectors:
        if detconfig.check_ntp_sync is None:
            detconfig.check_ntp_sync = ((configuration.ntp_server is not None) and 
                                        (configuration.ntp_server != ""))


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
        "-fg",
        "--foreground",
        dest="foreground",
        help="Run in foreground",
        default="False",
        action="store_true",
    )

    parser.add_argument(
        "action",
        choices=[
            "run",
            "gui",
            "query",
            "quit",
            "calibrate",
            "background",
            "listserialports",
            "listlabjacks",
        ],
        default="run",
        help="""Action to perform
    
    RADON DETECTOR ACTIONS
    These actions need a configuration file to be specified (using the -c or --config option)

    run
    Run the monitoring process in the background (unless the -fg or --foreground option is also given)
    
    query
    Display status of the monitoring process and exit
    
    quit
    Terminate the monitoring process
    
    calibrate
    Ask the monitoring process to begin a calibration sequence
    
    background
    Ask the monitoring process to  begin a background sequence
    
    AUXILLARY ACTIONS
    These actions do not require a configuration file

    listserialports
    List all serial ports on the system

    listlabjacks
    List all labjack U12s connected to the system
    """,
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
    print(args, cmdline_args)

    if raw_cfg is None:
        if cmdline_args.configuration_file.exists():
            raw_cfg = raw_config_from_inifile(cmdline_args.configuration_file)
        else:
            _logger.error(
                f'Configuration file "{cmdline_args.configuration_file}" does not exist.'
            )
            get_parser().print_help(sys.stderr)
            sys.exit(1)
    else:
        raw_cfg = copy.deepcopy(raw_cfg)

    # over-write config where options have been specified on the command line
    for k in ["loglevel", "foreground"]:
        val = vars(cmdline_args)[k]
        if val is not None:
            raw_cfg[k] = val

    print(raw_cfg)

    config = parse_config(raw_cfg)

    # validate configuration
    # (doing this early seems helpful, but may not be ideal in some respects.
    # Consider moving it later, e.g. when DataStore is initialized)
    if not config.data_dir.exists():
        _logger.error(f'Data storage directory "{config.data_dir}" does not exist.')

    # check log file is writable
    if config.logfile is None:
        config.logfile = config.data_dir.joinpath("radon_monitor_messages.log")
    try:
        with open(config.logfile, "at") as fd:
            pass
    except:
        _logger.error(
            f"Unable to open log file for writing, log messages will"
            f" not be saved.  Filename: {config.logfile}"
        )
        config.logfile = None
    _logger.debug(f"Configuration parsed: {config}")

    return config, cmdline_args


def config_from_yamlfile(filename) -> Configuration:
    filename = os.path.normpath(filename)
    _logger.info(f"Loading configuration from: {filename}")
    with open(filename, "rt") as fd:
        raw_cfg = yaml.safe_load(fd.read())
    config = parse_config(raw_cfg)
    return config


def config_from_inifile(filename) -> Configuration:
    """Read configuration from an ini file

    Parameters
    ----------
    filename : path
        filename, e.g. config.ini

    Returns
    -------
    Configuration
        Parsed configuration
    
    Note
    ----

    The ini file is assumed to have sections [data], [calbox], and
    one or more [detector...] sections (e.g. [detector1], [detector2])

    """
    raw_cfg = raw_config_from_inifile(filename)
    config = parse_config(raw_cfg)
    return config

def raw_config_from_inifile(filename) -> typing.Dict:
    """read configuration from inifile as a dict
    See also config_from_inifile

    Parameters
    ----------
    filename : str
        file path

    Returns
    -------
    Dict
        dict of configuration
    """
    filename = os.path.normpath(filename)
    _logger.info(f"Loading configuration from: {filename}")
    configp = configparser.ConfigParser()
    configp.read(filename)
    # load the detectors into an array of dicts
    detectors_config = []
    raw_cfg: typing.Dict[str, typing.Any] = {}
    for section in configp.sections():
        if section.startswith("detector"):
            detectors_config.append(dict(configp[section]))
        # config items under "data" are translated to top-level keys
        elif section == "data":
            raw_cfg.update(configp["data"])
        else:
            raw_cfg[section] = dict(configp[section])
    raw_cfg["detectors"] = detectors_config
    return raw_cfg


if __name__ == "__main__":
    raw_cfg = {
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


def setup_logging(loglevel=logging.DEBUG, logfn=None):
    """Setup basic logging

    Args:
        loglevel (int): minimum loglevel for emitting messages
        logfn (str): file name to log messages to (if None, don't log messages to file)

    """
    # exclude information messages for Pylink and Pycr1000
    for mod in ["pycampbellcr1000", "pylink"]:
        logging.getLogger(mod).setLevel(logging.CRITICAL)

    rootlogger = logging.getLogger()
    rootlogger.setLevel(loglevel)
    # logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    log_format = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d %(threadName)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S%z"

    # add a stream handler if non is present
    if len(rootlogger.handlers) == 0:
        stream_handler = StreamHandler(sys.stderr)
        stream_handler.setLevel(loglevel)
        rootlogger.addHandler(stream_handler)

    if logfn is not None:
        # check for existing RotatingFileHandlers and remove them
        for hdlr in rootlogger.handlers:
            if isinstance(hdlr, RotatingFileHandler):
                rootlogger.removeHandler(hdlr)

        file_handler = RotatingFileHandler(
            logfn,
            mode="a",
            maxBytes=5 * 1024 * 1024,
            backupCount=10,
            encoding=None,
            delay=0,
        )
        log_formatter = logging.Formatter(log_format, datefmt=datefmt)
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(loglevel)
        rootlogger.addHandler(file_handler)

    log_formatter = logging.Formatter(log_format, datefmt=datefmt)
    for hdlr in rootlogger.handlers:
        hdlr.formatter = log_formatter

