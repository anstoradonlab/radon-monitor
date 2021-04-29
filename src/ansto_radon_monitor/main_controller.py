"""
The main class which controls worker threads.

All functions are intended to return quickly, and then the class should later be polled for state

TODO: investigate use of https://docs.python.org/3/library/sched.html for timing

"""

import datetime
import logging
import math
import os
import sched
import signal
import threading
import time
import copy

import zerorpc

if os.name == "posix":
    from daemonize import Daemonize
else:
    Daemonize = None
import sys

_logger = logging.getLogger(__name__)
from ansto_radon_monitor.configuration import Configuration
from ansto_radon_monitor.datastore import DataStore

from .scheduler_threads import CalibrationUnitThread, DataLoggerThread


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
            # inside the child, start the daemon and exit the forked process
            daemon = Daemonize(app="ansto_radon_monitor", pid=pid, action=ipc_server)
            daemon.start()

        # IPC client
        c = zerorpc.Client()
        # TODO: what if the server isn't ready??  needs testing.
        c.connect("ipc:///tmp/ansto-radon-monitor.ipc")
        return c

    else:
        raise ValueError(f"Invalid mode: {mode}.")


class MainController(object):

    def __init__(self, configuration: Configuration):
        self.datastore = DataStore(configuration.data_dir)
        self._configuration = configuration
        self._start_threads()

    def _start_threads(self):
        thread_list = []
        # calibration unit
        self._cal_system_task = CalibrationUnitThread(
            labjack_id=self._configuration.labjack_id, datastore=self.datastore
        )
        thread_list.append(self._cal_system_task)

        # radon detector(s)
        for ii, detector_config in enumerate(self._configuration.detector_config):
            _logger.info(f"Setting up thread for detector {ii}")
            # note: poll the datalogger late (2 second measurement offset), so that it has a chance to update it's internal table
            # before being asked for data.
            t = DataLoggerThread(detector_config, datastore=self.datastore, measurement_offset=2)
            thread_list.append(t)

        for itm in thread_list:
            itm.start()

        self._threads = thread_list

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
        for itm in self._threads:
            itm.join()
        _logger.debug("Finished waiting for threads.")

    def terminate(self):
        """
        Terminate the entire process (most useful if running as ICP server)
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
        return t, copy.deepcopy(data)
    
    def list_tables(self):
        return self.datastore.tables


    def get_status(self):
        """
        return a tree of status information
        """
        # TODO: read status information from threads
        status = {'Detector 0': {'Datalogger': 'connected'} ,
                  'Cal unit': {'Mode': 'Normal operation'},
                  'Pending tasks': {'1999-31-21 23:59':'Fix y2k bug'}}
                                 
        return status
    
    def get_job_queue(self):
        """
        return a list of pending jobs
        """
        ret = ""
        for t in self._threads:
            ret += '\n' + t.name + '\n'
            try:
                ret += t.status + '\n  '
            except:
                ret += "[[no status message, t.status]]\n  "
            ret += '\n  '.join(t.task_queue)
            
        return ret
    
    def get_log_messages(self, start_time=None):
        """
        get all of the log messages stored since start_time
        """
        t = None
        return t, "Log messages not yet available"


    def run_calibration(self, flush_duration=10*3600, inject_duration=5*3600, radon_detector=0, start_time=None):
        self._cal_system_task.run_calibration(flush_duration, inject_duration, start_time=None)
    
    def run_background(self, duration=12*3600, start_time=None):
        self._cal_system_task.run_background(duration, start_time=None)
    
    def stop_calibration(self):
        self._cal_system_task.set_default_state()

    def stop_background(self):
        self._cal_system_task.cancel_background()
