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
import traceback

import ansto_radon_monitor

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
from ansto_radon_monitor.configuration import (Configuration, setup_logging)
from ansto_radon_monitor.datastore import DataStore
from ansto_radon_monitor.html import get_html_page

from .scheduler_threads import (CalibrationUnitThread, DataLoggerThread,
                                DataMinderThread, MockDataLoggerThread)


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
        'daemon', 'thread', 'connect', or 'foreground', by default 'thread'


    Returns a main controller proxy (or perhaps a main controller itself, if running threaded)
    """

    def ipc_server(mode="daemon"):
        # ref: http://www.zerorpc.io/
        # NOTE: if zerorpc becomes a problem, consider switching to
        # https://jsonrpcserver.readthedocs.io/en/latest/examples.html
        controller = MainController(configuration)
        s = zerorpc.Server(controller)
        s.bind("ipc:///tmp/ansto-radon-monitor.ipc")

        # if mode == "foreground":
        #    # TODO: this isn't working properly (need to hit ctrl-C twice)
        #    # check out this for a solution: https://gist.github.com/shiplu/0f1fd2f2a06519d0530c92533e18f264
        #    register_sigint_handler(controller.shutdown_and_exit)
        register_sigint_handler(controller.shutdown_and_exit)
        # take over logging
        setup_logging(configuration.loglevel, configuration.logfile, configuration.log_pakbus_activity)
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
        self.status = ""  # nothing to report unless things all go bad!
        self.cancelled = False
        self.state_changed = threading.Event()
        self.poll_interval = 10
        self._shutdown_detected = False

    def shutdown(self):
        self.cancelled = True
        self.state_changed.set()

    def run(self):
        while True:
            self.state_changed.wait(timeout=self.poll_interval)
            if self.cancelled:
                return
            if not self._shutdown_detected and self._main_controller._shutting_down:
                # at this point the main controller is shutting
                # down.  Take a break from monitoring and check back later
                self._shutdown_detected = True
                self.poll_interval = 60 * 3
                continue

            fail_count = 0
            #
            # ... check for stopped threads
            #
            with self._main_controller._thread_list_lock:
                for t in self._main_controller._threads:
                    if not t.is_alive():
                        if hasattr(t, "exc_info") and t.exc_info is not None:
                            try:
                                exc_type, exc_value, exc_traceback = t.exc_info
                                info = f"{exc_type}: {exc_value} {traceback.format_tb(exc_traceback)}"
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
            #
            # ... check for hung threads and report
            #
            with self._main_controller._thread_list_lock:
                for t in self._main_controller._threads:
                    # TODO: move to variable, or configuration
                    if not hasattr(t, "heartbeat_age"):
                        # not a DataThread, no need to monitor
                        continue
                    age = t.heartbeat_age
                    if age > t.max_heartbeat_age_seconds:
                        _logger.error(
                            f"Thread {t.name} appears to be stuck (no heartbeat for {age} seconds).  A stack trace of all threads follows:"
                        )
                        for th in threading.enumerate():
                            _logger.error(f"Thread {th}")
                            msg = "".join(
                                traceback.format_stack(sys._current_frames()[th.ident])
                            )
                            _logger.error(f"{msg}")


class MainController(object):
    def __init__(self, configuration: Configuration):
        self._thread_list_lock = threading.RLock()
        try:
            self.datastore = DataStore(configuration)
        except Exception as ex:
            _logger.critical(
                f"Unable to open database because of error: {ex}, {traceback.format_exc()}"
            )
            raise ex
        
        # indicate that NTP checks haven't yet been performed (since startup) 
        self.datastore.set_state("NTPOffset", None)

        # a flag used to signal that the controller is shutting down
        self._shutting_down = False
        self._configuration = configuration
        logging.info(f"RDM version {ansto_radon_monitor.__version__}")
        # a publicly accessible flag to indicate whether or not there is a calibration
        # unit present
        self.has_calibration_unit = False
        try:
            self._start_threads()
            self.datastore.add_log_message("SystemEvent", "Startup")
            self.datastore.add_log_message("ConfigurationDump", configuration.as_text())
        except Exception as ex:
            _logger.critical(
                f"Unable to start logging because of error: {ex}, {traceback.format_exc()}"
            )
            self.shutdown()
            raise ex

    def _start_threads(self):
        with self._thread_list_lock:
            self._threads = []

        # calibration unit
        if not self._configuration.calbox.kind.lower() == 'none':
            self._cal_system_task = CalibrationUnitThread(
                self._configuration, datastore=self.datastore
            )
            with self._thread_list_lock:
                self._threads.append(self._cal_system_task)
            self.has_calibration_unit = True
        else:
            self._cal_system_task = None
            self.has_calibration_unit = False
            

        # radon detector(s)
        mock_detector_kinds = ["mock"]
        real_detector_kinds = ["L5000", "L1500", "L700", "L200", "L100"]
        known_detector_kinds = mock_detector_kinds + real_detector_kinds
        for ii, detector_config in enumerate(self._configuration.detectors):
            _logger.info(
                f"Setting up thread for detector {ii+1} (type of detector: {detector_config.kind})"
            )
            if detector_config.kind in mock_detector_kinds:
                t = MockDataLoggerThread(
                    detector_config, datastore=self.datastore, measurement_offset=2
                )
            elif detector_config.kind in real_detector_kinds:
                # note: poll the datalogger late (2 second measurement offset), so that it has a chance to update it's internal table
                # before being asked for data.
                t = DataLoggerThread(
                    detector_config, datastore=self.datastore, measurement_offset=2
                )
            else:
                raise NotImplementedError(
                    f"Logging for detector of kind '{detector_config.kind}' is not implemented.  Known detector kinds are: {known_detector_kinds}"
                )
            with self._thread_list_lock:
                self._threads.append(t)

        # a thread to schedule backups and exports from the database
        with self._thread_list_lock:
            t = DataMinderThread(self._configuration, datastore=self.datastore)
            self._data_minder_task = t
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
        this_is_main_thread = threading.main_thread() == threading.current_thread()
        self.datastore.add_log_message("SystemEvent", "Shutdown")
        self._shutting_down = True
        _logger.info("Asking threads to shut down.")
        wait_list = []
        # Shut down threads other than the MonitorThread first, that way the MonitorThread
        # will still be around to report on what the other threads are doing if there are
        # problems during shutdown
        for itm in self._threads:
            if not itm.name == "MonitorThread":
                itm.shutdown()
                wait_list.append(itm)
        for itm in wait_list:
            _logger.info(f"Waiting for {itm.name}")
            itm.join(timeout=30)
            if itm.is_alive():
                _logger.error(f'Thread {itm.name} is still running after waiting for 30s')
                msg = "".join(
                                traceback.format_stack(sys._current_frames()[itm.ident])
                            )
                _logger.error(f'Thread {itm.name} stack trace: {msg}')

        # if the MonitorThread has asked us to shutdown, we'll fail to close the mainthread's database
        # connection, but this is Ok (it will be cleaned up next the the program runs)
        if this_is_main_thread:
            self.datastore.shutdown()

        # finally, shut down the MonitorThread
        for itm in self._threads:
            if itm.name == "MonitorThread":
                itm.shutdown()
                if not threading.current_thread() is itm:
                    # it's possible to call shutdown from MonitorThread, so don't wait 
                    # on the current thread
                    _logger.info(f"Waiting for {itm.name}")
                    itm.join(timeout=30)
                    if itm.is_alive():
                        _logger.error(f'Thread {itm.name} is still running after waiting for 30s')
                        msg = "".join(
                                        traceback.format_stack(sys._current_frames()[itm.ident])
                                    )
                        _logger.error(f'Thread {itm.name} stack trace: {msg}')

        _logger.info("All threads have finished shutting down.")
        # check for active threads - only MainThread or the current thread (which is most likely to be
        # the MainThread, but might also be MonitorThread) should still be running.
        for itm in threading.enumerate():
            if not (itm == threading.main_thread() or itm == threading.current_thread()):
                _logger.error(f"A thread is still alive after shutdown: {itm}")
        

    def shutdown_and_exit(self):
        """
        Ask threads to finish then exit process
        """
        self.shutdown()
        sys.exit(0)

    def terminate(self):
        """
        Terminate the entire process (most useful if running as IPC server)
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
            sys.exit(1)

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
        if self._shutting_down:
            return (None, [])
        t, data = self.datastore.get_rows(table, start_time)
        # converts dates into timestamps, which can be serialised
        # for transparent inter-process communication
        data = copy.deepcopy(data)
        for itm in data:
            if "Datetime" in itm:
                itm["Datetime"] = itm["Datetime"].timestamp()
        
        return t, data

    def list_tables(self):
        return self.datastore.tables

    def list_data_tables(self):
        return self.datastore.data_tables

    def html_current_measurement(self):
        """Return a html representation of the current measurement state"""
        fragments = []
        for t in self._threads:
            if hasattr(t, "html_current_status"):
                fragments.append(t.html_current_status())
        html = get_html_page(fragments)
        return html

    def get_status(self):
        """
        return a tree of status information
        """
        summary_dict = {}
        status = {}
        detector_names = []
        for t in self._threads:
            if t.name.startswith("DataLoggerThread"):
                k = t.detectorName
                detector_names.append(k)
            else:
                k = t.name
            status[k] = {"status": t.status}

        status["pending tasks"] = self.get_job_queue()

        status["_pending tasks"] = self.get_job_queue(pyobjects=True)

        # summarise the status information into a single line
        # summary is something like:
        #  TEST_002M  link: connected, serial: COM1  TEST_050M  link: connected, serial: COM2
        summary_list = []
        for k in detector_names:
            # itm_summary = ','.join([
            #        f'{itmkey}: {str(itmvalue)}' for itmkey,itmvalue in zip(status[k]['status'].items())
            #    ])
            itm_summary = (
                str(status[k]["status"])
                .replace("{", "")
                .replace("}", "")
                .replace("'", "")
            )
            summary_list.append(f"{k}   {itm_summary}")

        if self.has_calibration_unit:
            summary_cal = f"Calibration Unit    {status['CalibrationUnitThread']['status']['message']}"
            summary_list.append(summary_cal)

        status["summary"] = " | ".join(summary_list)
        return status

    def get_job_queue(self, pyobjects=False):
        """
        return a list of pending jobs
        """
        jobq = []
        if pyobjects:
            # return dict of python objects, for downstream programs
            for t in self._threads:
                try:
                    jobq.extend(t.pydict_task_queue)
                except AttributeError:
                    # some threads (e.g. MonitorThread) don't have a task queue
                    pass

        else:
            # return string info, for display to users
            for t in self._threads:
                # only report on the calibration unit & data minder
                if t.name == "CalibrationUnitThread" or t.name == "DataMinderThread":
                    jobq.append(t.task_queue)

        return jobq

    def get_log_messages(self, start_time=None):
        """
        get all of the log messages stored since start_time
        """
        t = None
        return t, "Log messages not yet available"

    def backup_now(self):
        """
        Run the backup/csv output/file upload tasks (syncing csv
        output from the archive files as well as the active database)
        """
        self._data_minder_task.schedule_database_tasks(include_archives=True)


    def run_calibration(
        self,
        flush_duration=10 * 3600,
        inject_duration=5 * 3600,
        start_time=None,
        detector_idx=0,
    ):
        if self._cal_system_task is None:
            _logger.error(
                            f"Attempted perform calibration function but a calibration unit is not configured.  {traceback.format_exc()}"
                        )
            return
        self._cal_system_task.run_calibration(
            flush_duration,
            inject_duration,
            start_time=start_time,
            detector_idx=detector_idx,
        )

    def run_background(self, duration=12 * 3600, start_time=None, detector_idx=0):
        if self._cal_system_task is None:
            _logger.error(
                            f"Attempted perform calibration function but a calibration unit is not configured.  {traceback.format_exc()}"
                        )
            return
        self._cal_system_task.run_background(
            duration, start_time=start_time, detector_idx=detector_idx
        )

    def stop_calibration(self):
        if self._cal_system_task is None:
            _logger.error(
                            f"Attempted perform calibration function but a calibration unit is not configured.  {traceback.format_exc()}"
                        )
            return
        self._cal_system_task.cancel_calibration()

    def stop_background(self):
        if self._cal_system_task is None:
            _logger.error(
                            f"Attempted perform calibration function but a calibration unit is not configured.  {traceback.format_exc()}"
                        )
            return
        self._cal_system_task.cancel_background()

    def schedule_recurring_calibration(
        self,
        flush_duration,
        inject_duration,
        t0_cal,
        cal_interval,
        detector_idx=0,
    ):
        if self._cal_system_task is None:
            _logger.error(
                            f"Attempted perform calibration function but a calibration unit is not configured.  {traceback.format_exc()}"
                        )
            return
        self._cal_system_task.schedule_recurring_calibration(
            flush_duration,
            inject_duration,
            t0_cal,
            cal_interval,
            detector_idx,
        )

    def schedule_recurring_background(
        self,
        duration,
        t0_background,
        background_interval,
        detector_idx=0,
    ):
        if self._cal_system_task is None:
            _logger.error(
                            f"Attempted perform calibration function but a calibration unit is not configured.  {traceback.format_exc()}"
                        )
            return
        self._cal_system_task.schedule_recurring_background(
            duration,
            t0_background,
            background_interval,
            detector_idx,
        )

    def cal_and_bg_is_scheduled(self):
        """return true if it looks like a bg and cal are scheduled"""
        return self._cal_system_task is None or self._cal_system_task.cal_and_bg_is_scheduled()

    def get_cal_running(self):
        return self._cal_system_task is None or self._cal_system_task.cal_running

    def get_bg_running(self):
        return self._cal_system_task is None or self._cal_system_task.bg_running

    def get_maintenance_mode(self):
        k = "Maintenance Mode"
        default_value = False
        mm = self.datastore.get_state(k)
        if mm is None:
            # default value
            mm = default_value
            # write this into the database
            self.datastore.set_state(k, default_value)

        return bool(mm)

    def set_maintenance_mode(self, mm_active):
        k = "Maintenance Mode"
        mm_old = self.maintenance_mode
        if not (mm_active == mm_old):
            _logger.info(f"Toggling maintenance mode from {mm_old} to {mm_active}")
            self.datastore.add_log_message("MaintenanceMode", mm_active)
            self.datastore.set_state(k, mm_active)
