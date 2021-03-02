"""
The main class which controls worker threads.

All functions are intended to return quickly, and then the class should later be polled for state

TODO: investigate use of https://docs.python.org/3/library/sched.html for timing

"""

import datetime
import logging
import math
import os
import signal
import threading
import time

import zerorpc

if os.name == "posix":
    from daemonize import Daemonize
else:
    Daemonize = None
import sys

_logger = logging.getLogger(__name__)
from ansto_radon_monitor.configuration import Configuration
from ansto_radon_monitor.datastore import DataStore


def setup_logging(loglevel, logfile=None):
    """Setup basic logging

    Args:
        loglevel (int): minimum loglevel for emitting messages
    """
    # logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logformat = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d %(threadName)s] %(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )


def initialize(configuration: Configuration, mode: str = "thread"):
    """Start up the MainController object.  If it is already running, then try to connect to it.

    Parameters
    ----------
    configuration : dict-like
        program options
    mode : str, optional
        'daemon', 'thread', or 'foreground', by default 'daemon'
    

    Returns a main controller proxy (or perhaps a main controller itself, if running threaded)
    """

    def ipc_server():
        # ref: http://www.zerorpc.io/
        # NOTE: if zerorpc becomes a problem, consider switching to
        # https://jsonrpcserver.readthedocs.io/en/latest/examples.html
        setup_logging(configuration.loglevel, configuration.logfile)
        s = zerorpc.Server(MainController(configuration))
        s.bind("ipc:///tmp/ansto-radon-monitor.ipc")
        s.run()

    if mode == "foreground":
        # never returns
        ipc_server()

    elif mode == "thread":
        # MainController spawns threads as required to avoid blocking,
        # just return the controller object
        controller = MainController(configuration)
        return controller

    elif mode == "daemon" and os.name != "posix":
        raise ValueError(f'"Daemon" mode is only supported on posix systems.')

    elif mode == "daemon":

        pid = configuration.pid_file
        # daemon ref: https://github.com/thesharp/daemonize
        process_id = os.fork()
        if process_id == 0:
            # inside the child, start the daemon and exit
            daemon = Daemonize(app="ansto_radon_monitor", pid=pid, action=ipc_server)
            daemon.start()

        # IPC client
        c = zerorpc.Client()
        # TODO: what if the server isn't ready??  needs testing.
        c.connect("ipc:///tmp/ansto-radon-monitor.ipc")
        return c

    else:
        raise ValueError(f"Invalid mode: {mode}.")
    # if thread, then call threading.Thread

    # if daemon then call
    # from daemonize import Daemonize
    # pid = "/tmp/ansto-radon-monitor.pid"
    # daemon = Daemonize(app="test_app", pid=pid, action=main, keep_fds=keep_fds)
    # daemon.start()

    # daemon will need to
    pass


class MainController(object):

    # TODO: write app options class and pass it here
    def __init__(self, app_options=None):
        self.datastore = DataStore()
        self._start_threads()

    def _start_threads(self):
        thread_list = []
        self._cal_system_task = CalSystemThread(datastore=self.datastore)
        thread_list.append(self._cal_system_task)

        for itm in thread_list:
            itm.start()

        self._threads = thread_list

    def shutdown(self):
        _logger.debug("Asking threads to shut down.")
        for itm in self._threads:
            itm.shutdown()
        _logger.debug("Waiting for threads...")
        for itm in self._threads:
            itm.join()
        _logger.debug("Finished waiting for threads.")

    def terminate(self):
        """
        Terminate the entire process (most useful if running as server)
        """
        self.shutdown()

        # the following allows the shutdown to happen asynchronously
        # in the background, while still returning to the caller
        def delayed_exit():
            time.sleep(10)
            # use sigterm, to give daemon a chance to clean up
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(10)
            # should not get here
            sys.exit(0)

        t = threading.Thread(target=delayed_exit, daemon=True)
        t.start()
        return "Ok - exiting in 10 sec"


def round_up_time(
    dt: datetime.datetime = None, round_to: float = 60
) -> datetime.datetime:
    """Round a datetime up to the nearest interval of `round_to` seconds

    Parameters
    ----------
    dt : datetime.datetime, optional
        datetime to round, by default None (use the current time if None)
    round_to : float, optional
        Number of seconds, by default 60

    Returns
    -------
    datetime.datetime
        Rounded time
    """
    if dt is None:
        dt = datetime.datetime.utcnow()
    midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_since_midnight = (dt - midnight).total_seconds()
    rounded_seconds = math.ceil(seconds_since_midnight / round_to) * round_to
    # _logger.debug(f'{midnight}, {dt}, {midnight + datetime.timedelta(seconds=rounded_seconds)}')
    return midnight + datetime.timedelta(seconds=rounded_seconds)


def sleep_until_multiple_of(interval):
    """try to sleep for a duration which ends on a multiple of `interval` seconds"""
    now = datetime.datetime.utcnow()
    wake_time = round_up_time(now, interval)
    sleep_duration = (wake_time - now).total_seconds()
    if sleep_duration < interval / 2.0:
        sleep_duration += interval
    if sleep_duration < interval / 2.0 or interval * 1.01 < interval:
        _logger.error(
            f"Unexpected sleep duration {sleep_duration}, setting to {interval}"
        )
        sleep_duration = interval
    # _logger.debug(f'Sleeping for {sleep_duration}sec')
    time.sleep(sleep_duration)


# TODO: move common features to a base class


class DataThread(threading.Thread):
    pass


class DataLoggerThread(threading.Thread):
    def __init__(self, datastore, *args, **kwargs):
        kwargs["name"] = "DataLoggerThread"
        self._datastore = datastore
        self.alive = True
        self._tick_interval = 0.1
        self.measurement_interval = 10  # TODO: from config

    def shutdown(self):
        self.alive = False
        _logger.debug("Thread shutdown requested.")

    def run(self):
        _logger.debug("Started cal system control thread.")
        # TODO: replace self.alive with a threading.Event
        while self.alive:
            self.maybe_take_sample()
            sleep_until_multiple_of(self._tick_interval)

        _logger.debug("Stopping cal system control thread.")


# TODO: handle INT (ctrl-C) signal (https://www.cloudcity.io/blog/2019/02/27/things-i-wish-they-told-me-about-multiprocessing-in-python/)


class CalSystemThread(threading.Thread):
    def __init__(self, datastore, *args, **kwargs):
        kwargs["name"] = "CalSystemThread"
        self._datastore = datastore
        self.alive = True
        # TODO: maybe replace with priority queue?
        # TODO: or a scheduler https://docs.python.org/3/library/sched.html
        self.scheduled_tasks = []
        self._tick_interval = 0.1
        self.measurement_interval = 10  # TODO: from config
        self._last_measurement_time = None
        self._measurement_due = None
        super().__init__(*args, **kwargs)

    def shutdown(self):
        self.alive = False
        _logger.debug("Thread shutdown requested.")

    def take_sample(self):
        """Take sample from the cal system immediately"""
        data = {"time": datetime.datetime.utcnow(), "state": "open"}
        return data

    def maybe_take_sample(self):
        """grab the state from the cal system, if it's time
        
        Notes: manages `_last_measurement_time` and `_measurement_due`
        """
        if self._measurement_due is None:
            self._measurement_due = round_up_time(round_to=self.measurement_interval)
            _logger.debug(f"Setting first measurement time to {self._measurement_due}.")
            return

        t = datetime.datetime.utcnow()
        if t >= self._measurement_due:
            sample = self.take_sample()
            _logger.debug("Sample acquired from cal system.")
            self._last_measurement_time = self._measurement_due
            self._measurement_due += datetime.timedelta(
                seconds=self.measurement_interval
            )
            self._datastore.add_record("cal_system", sample)

    def run(self):
        _logger.debug("Started cal system control thread.")
        # TODO: replace self.alive with a threading.Event
        while self.alive:
            self.maybe_take_sample()
            sleep_until_multiple_of(self._tick_interval)

        _logger.debug("Stopping cal system control thread.")
