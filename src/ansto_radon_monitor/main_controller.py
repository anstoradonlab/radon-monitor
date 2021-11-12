"""
The main class which controls worker threads.

All functions are intended to return quickly, and then the class should later be polled for state

"""

import copy
import datetime
import logging
import math
import os
import sched
import signal
import threading
import time

# don't use zeropc on windows because it causes firewall-related messages
if os.name == "posix":
    import zerorpc
else:
    zeropc = None

if os.name == "posix":
    from daemonize import Daemonize
else:
    Daemonize = None
import sys

_logger = logging.getLogger(__name__)
from ansto_radon_monitor.configuration import Configuration
from ansto_radon_monitor.datastore import DataStore

from .scheduler_threads import (CalibrationUnitThread, DataLoggerThread,
                                MockDataLoggerThread, DataMinderThread)


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


def register_sigint_handler(callback_func):
    """
    Register a signal handler to gracefully shut down when the user presses Ctrl-C

    Alternative approach:
    https://gist.github.com/shiplu/0f1fd2f2a06519d0530c92533e18f264
    """
    _logger.debug("Registering SIGING signal handler")

    def signal_handler(sig, frame):
        _logger.info("Received interrupt signal, shutting down.")
        callback_func()

    signal.signal(signal.SIGINT, signal_handler)


def initialize(configuration: Configuration, mode: str = "thread"):
    """Start up the MainController object.  If it is already running, then try to connect to it.

    Parameters
    ----------
    configuration : dict-like
        program options
    mode : str, optional
        'daemon', 'thread', 'connect', or 'foreground', by default 'daemon'


    Returns a main controller proxy (or perhaps a main controller itself, if running threaded)
    """

    def ipc_server(mode="daemon"):
        # ref: http://www.zerorpc.io/
        # NOTE: if zerorpc becomes a problem, consider switching to
        # https://jsonrpcserver.readthedocs.io/en/latest/examples.html
        setup_logging(configuration.loglevel, configuration.logfile)
        controller = MainController(configuration)
        s = zerorpc.Server(controller)
        s.bind("ipc:///tmp/ansto-radon-monitor.ipc")

        # if mode == "foreground":
        #    # TODO: this isn't working properly (need to hit ctrl-C twice)
        #    # check out this for a solution: https://gist.github.com/shiplu/0f1fd2f2a06519d0530c92533e18f264
        #    register_sigint_handler(controller.shutdown_and_exit)
        register_sigint_handler(controller.shutdown_and_exit)
        s.run()

    if mode == "foreground":
        if os.name == "posix":
            pid = configuration.pid_file
            # daemon ref: https://github.com/thesharp/daemonize
            # inside the child, start the daemon and exit the forked process
            daemon = Daemonize(
                app="ansto_radon_monitor",
                pid=pid,
                action=ipc_server,
                logger=_logger,
                foreground=True,
            )
            daemon.start()
        else:
            # Windows version
            # never returns and is not prevented from running multiple instances of the program
            # it is likely that the program will fail when trying to open a serial port if there
            # is already a version of this app running.
            ipc_server(mode=mode)

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
            # inside the child, start the daemon and exit the forked process
            daemon = Daemonize(
                app="ansto_radon_monitor", pid=pid, action=ipc_server, logger=_logger
            )
            daemon.start()

        # IPC client
        c = zerorpc.Client()
        # TODO: what if the server isn't ready??  needs testing.
        c.connect("ipc:///tmp/ansto-radon-monitor.ipc")
        return c

    elif mode == "connect":
        _logger.info("Attempting to connect to a running background process")
        # connect to running background process
        # IPC client
        c = zerorpc.Client()
        # TODO: what if the server isn't running?  needs testing.
        c.connect("ipc:///tmp/ansto-radon-monitor.ipc")
        return c

    else:
        raise ValueError(f"Invalid mode: {mode}.")


class MonitorThread(threading.Thread):
    """
    This thread periodically checks on the health of a list of threads
    """

    def __init__(self, main_controller, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._main_controller = main_controller
        self.name = "MonitorThread"
        self.cancelled = False
        self.state_changed = threading.Event()

    def shutdown(self):
        self.cancelled = True
        self.state_changed.set()

    def run(self):
        while True:
            self.state_changed.wait(timeout=10)
            if self.cancelled:
                return
            fail_count = 0
            with self._main_controller._thread_list_lock:
                for t in self._main_controller._threads:
                    if not t.is_alive():
                        if hasattr(t, "exc_info") and t.exc_info is not None:
                            try:
                                exc_type, exc_value, exc_traceback = t.exc_info
                                import traceback

                                info = f"{type(exc_type)}: {exc_value} {traceback.format_tb(exc_traceback)}"
                            except Exception as ex:
                                info = f" Failed to obtain exec_info due to error: {ex}"
                        else:
                            info = ""
                        _logger.critical(
                            f"Thread {t.name} has stopped unexpectedly.{info}"
                        )
                        # even though a failure has been detected, continue to loop through the entire
                        # list of threads so that a simultaneous failure will still appear in the logs
                        fail_count += 1
            if fail_count > 0:
                # at least for now, let's bring the whole thing down
                # self._main_controller.shutdown_and_exit()
                self._main_controller.terminate()
                # TODO: the thread should not be crashing - it should be handling the error
                # internally.
                # TODO: the behaviour here maybe should depend on how the logger is being called.
                # If it's a library called by the GUI, perhaps it would make sense for
                # just to shut down and then set a status e.g. "STOPPED" in the GUI
                # so that the user has a chance to restart (or the GUI could make an
                # automatic attempt to re-start after a countdown expires)


class MainController(object):
    def __init__(self, configuration: Configuration):
        self._thread_list_lock = threading.RLock()
        self.datastore = DataStore(configuration)
        self._configuration = configuration
        self._start_threads()

    def _start_threads(self):
        with self._thread_list_lock:
            self._threads = []

        # calibration unit
        self._cal_system_task = CalibrationUnitThread(
            self._configuration.calbox, datastore=self.datastore
        )
        with self._thread_list_lock:
            self._threads.append(self._cal_system_task)

        # radon detector(s)
        for ii, detector_config in enumerate(self._configuration.detectors):
            _logger.info(
                f"Setting up thread for detector {ii} (type of detector: {detector_config.kind})"
            )
            if detector_config.kind == "mock":
                t = MockDataLoggerThread(
                    detector_config, datastore=self.datastore, measurement_offset=2
                )
            elif detector_config.kind in ["L1500", "L750", "L200", "L100"]:
                # note: poll the datalogger late (2 second measurement offset), so that it has a chance to update it's internal table
                # before being asked for data.
                t = DataLoggerThread(
                    detector_config, datastore=self.datastore, measurement_offset=2
                )
            else:
                raise NotImplementedError(
                    f"Logging for detector of kind '{detector_config.kind}' is not implemented."
                )
            with self._thread_list_lock:
                self._threads.append(t)

        # a thread to schedule backups and exports from the database
        with self._thread_list_lock:
            t = DataMinderThread(self._configuration, datastore=self.datastore)
            self._threads.append(t)

        # set up a thread to monitor self
        # this thread accesses self._threads , hence the lock
        # note - I don't think the lock is really required, but it helps to remind
        # me that the list of threads is accessed from multiple threads
        with self._thread_list_lock:
            t = MonitorThread(self)
            self._threads.append(t)

        with self._thread_list_lock:
            for itm in self._threads:
                itm.start()

    def shutdown(self):
        """
        Stop all activity in threads
        """
        _logger.debug("Asking threads to shut down.")
        for itm in self._threads:
            itm.shutdown()
        _logger.debug("Shutting down datastore.")
        self.datastore.shutdown()
        _logger.debug("Waiting for threads...")
        if (threading.main_thread()).ident == threading.get_ident():
            # TODO: decide what *should* happen if shutdown is called from a thread other than the main one
            for itm in self._threads:
                itm.join()
        _logger.debug("Finished waiting for threads.")

    def shutdown_and_exit(self):
        """
        Ask threads to finish then exit process
        """
        self.shutdown()
        sys.exit(0)

    def terminate(self):
        """
        Terminate the entire process (most useful if running as ICP server)
        """
        self.shutdown()

        # the following allows the shutdown to happen asynchronously
        # in the background, while still returning to the caller.
        # this avoids a 'broken pipe' message for the IPC client
        def delayed_exit():
            time.sleep(2)
            # use sigterm, to give daemon a chance to clean up
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(10)
            # should not get here
            sys.exit(0)

        t = threading.Thread(target=delayed_exit, daemon=True)
        t.start()
        return "Ok - exiting in 2 sec"

    def get_rows(self, table, start_time=None):
        """return the data from a data table, optionally just the
           data newer than `reference_time`

        Parameters
        ----------
        table : [type]
            [description]
        reference_time : [type]
            [description]
        """
        t, data = self.datastore.get_rows(table, start_time)
        return t, data

    def list_tables(self):
        return self.datastore.tables

    def get_status(self):
        """
        return a tree of status information
        """
        status = {}
        for t in self._threads:
            if t.name == "DataloggerThread":
                k = t.dataloggerName
            else:
                k = t.name
            status[k] = {"status": t.status}

        status["pending tasks"] = self.get_job_queue()

        return status

    def get_job_queue(self):
        """
        return a list of pending jobs
        """
        jobq = []
        for t in self._threads:
            # only report on the calibration unit
            if t.name == "CalibrationUnitThread":
                jobq = t.task_queue

        return jobq

    def get_log_messages(self, start_time=None):
        """
        get all of the log messages stored since start_time
        """
        t = None
        return t, "Log messages not yet available"

    def run_calibration(
        self,
        flush_duration=10 * 3600,
        inject_duration=5 * 3600,
        radon_detector=0,
        start_time=None,
    ):
        self._cal_system_task.run_calibration(
            flush_duration, inject_duration, start_time=None
        )

    def run_background(self, duration=12 * 3600, start_time=None):
        self._cal_system_task.run_background(duration, start_time=None)

    def stop_calibration(self):
        self._cal_system_task.cancel_calibration()

    def stop_background(self):
        self._cal_system_task.cancel_background()
