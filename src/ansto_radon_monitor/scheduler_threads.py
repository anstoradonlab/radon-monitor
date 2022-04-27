import collections
import copy
import datetime
import functools
import logging
import math
import pprint
import sched
import sys
import threading
import time
import traceback
from typing import Dict

import numpy as np
from pycampbellcr1000 import CR1000
from pycampbellcr1000.utils import ListDict

from ansto_radon_monitor.configuration import Configuration
from ansto_radon_monitor.datastore import DataStore
from ansto_radon_monitor.html import status_as_html

_logger = logging.getLogger()

from .labjack_interface import CalBoxLabjack


def log_backtrace_all_threads():
    for th in threading.enumerate():
        _logger.error(f"Thread {th}")
        # print(f"Thread {th}", file=sys.stderr)
        msg = "".join(traceback.format_stack(sys._current_frames()[th.ident]))
        _logger.error(f"{msg}")
        # print(f"{msg}", file=sys.stderr)


def task_description(description_text):
    """
    A decorator which adds a human-readable description to a function
    by adding an attribute called `description`.  The description is
    intended to be presented later to the user in a list of pending tasks.

    Usage:
    @describe("Adds two numbers")
    def add_two(a,b):
        return a+b

    print(add_two.description)
    """

    def desc_decorator(func):
        func.description = description_text
        return func

    return desc_decorator


def next_interval(sec, interval, offset=0.0):
    """calculate time when interval next expires

    Parameters
    ----------
    sec : type returned by time.time()
        now
    interval : [type]
        interval length (seconds)
    offset : float, optional
        offset for first interval, e.g. if interval is 10.0 and offset is 1.0,
        the interval will expire at 11.0, 21.0, ... sec

    Returns
    -------
    float
        time until next interval expires
    """
    # TODO: handle the offset (check it is getting used first)
    return (math.ceil(sec / interval) * interval) - sec


class DataThread(threading.Thread):
    """
    Base thread for data-oriented threads.  Sits in a loop and runs tasks,
    and can be shutdown cleanly from another thread.

    The implementation of scheduling is based on `sched` from the standard library
    https://docs.python.org/3/library/sched.html

    TODO: shut down the entire application if the thread encounters an unhandled exception
    """

    def __init__(
        self,
        datastore,
        run_measurement_on_startup=False,
        measurement_interval=10,
        measurement_offset=0,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.name = "DataThread"
        self.exc_info = None
        self._datastore = datastore
        self.cancelled = False
        self.state_changed = threading.Event()
        self._tick_interval = 0.1
        self.measurement_interval = measurement_interval  # TODO: from config
        self.measurement_offset = measurement_offset
        self._done = False
        self._last_measurement_time = 0
        self._scheduler = sched.scheduler(time.time, time.sleep)
        self._lock = threading.RLock()
        now = time.time()
        delay = next_interval(now, self.measurement_interval, self.measurement_offset)
        _logger.debug(f"next time: {delay+now} (next - now : {delay})")
        if run_measurement_on_startup:
            delay = 0
        self._scheduler.enter(delay=delay, priority=0, action=self.run_measurement)

        _logger.debug(f"Scheduler queue: {self._scheduler.queue}")

        # this is used for detecting a hang
        self._heartbeat_time_lock = threading.RLock()
        self._heartbeat_time = time.time()
        self._tolerate_hang = False

        self._scheduler.enter(delay=1, priority=0, action=self.update_heartbeat_time)

    def shutdown(self):
        self.cancelled = True
        self.state_changed.set()

    @property
    def done(self):
        return _done

    def update_heartbeat_time(self):
        with self._heartbeat_time_lock:
            self._heartbeat_time = time.time()
        self._scheduler.enter(delay=1, priority=0, action=self.update_heartbeat_time)

    @property
    def heartbeat_age(self):
        t = time.time()
        with self._heartbeat_time_lock:
            if self._tolerate_hang:
                age = 0.0
            else:
                age = t - self._heartbeat_time
        return age

    def measurement_func(self):
        _logger.debug(
            f"Taking measurement at {datetime.datetime.now(datetime.timezone.utc)}"
        )
        _logger.debug(f"Scheduler queue: {self._scheduler.queue}")

    def shutdown_func(self):
        _logger.debug(f"Shutdown function")

    @property
    def task_queue(self):
        """
        Human-readable version of the task queue
        """

        def time_to_text(t):
            fmt = "%Y-%m-%d %H:%M:%S"
            return datetime.datetime.fromtimestamp(t).strftime(fmt)

        def task_to_readable(task):
            t = time_to_text(task.time)
            try:
                desc = task.action.description
                return f"{t} {desc}"
            except AttributeError:
                return None

        with self._lock:
            ret = [task_to_readable(itm) for itm in self._scheduler.queue]
            ret = [itm for itm in ret if not itm is None]
        return ret

    @property
    def seconds_until_next_measurement(self):
        now = time.time()
        delay = next_interval(now, self.measurement_interval, self.measurement_offset)
        return delay

    # Don't describe this task
    # @task_description("Poll the measurement hardware")
    def run_measurement(self):
        """call measurement function and schedule next"""
        self.measurement_func()
        self._scheduler.enter(
            delay=self.seconds_until_next_measurement,
            priority=0,
            action=self.run_measurement,
        )

        _logger.debug(f"Scheduler queue: {self._scheduler.queue}")

    def run(self):
        try:
            _logger.debug(f"{self.name} has started running")
            time_until_next_event = 0.0
            while True:
                # wait until either the next task is due (at 'time_until_next_event')
                # or another thread causes a state change
                state_changed = self.state_changed.wait(timeout=time_until_next_event)
                if state_changed:
                    _logger.debug("State was changed.")
                self.state_changed.clear()
                if self.cancelled:
                    break
                else:
                    time_until_next_event = self._scheduler.run(blocking=False)
                    if time_until_next_event is None:
                        _logger.error(
                            "Expected to make a measurement, but no more events in scheduler."
                        )
                        time_until_next_event = self.measurement_interval

                    _logger.debug(f"Time until next event: {time_until_next_event}")

                    assert time_until_next_event >= 0
                    _logger.debug(f"Q: {self._scheduler.queue}")
                    _logger.debug(f"Task Queue: {self.task_queue}")

            _logger.debug(f"{self.name} has finished and will call shutdown_func()")
            self.shutdown_func()
        except Exception as ex:
            _logger.error(
                f"{self.name} is aborting with an unhandled exception. Stack trace for all threads follows."
            )
            for th in threading.enumerate():
                _logger.error(f"Thread {th}")
                # print(f"Thread {th}", file=sys.stderr)
                msg = "".join(traceback.format_stack(sys._current_frames()[th.ident]))
                _logger.error(f"{msg}")
                # print(f"{msg}", file=sys.stderr)

            self.exc_info = sys.exc_info()
            raise ex


class CalibrationUnitThread(DataThread):
    def __init__(self, config, datastore, *args, **kwargs):

        labjack_id = config.labjack_id
        serialNumber = config.labjack_serial

        # Labjack API needs None for serialNumber if we are to ignore it
        if serialNumber == -1:
            serialNumber = None
        # Note: this code is run in the main thread, so avoid doing anything which
        # might block here (instead, add tasks to the scheduler which is called
        # inside )
        super().__init__(datastore, *args, **kwargs)
        self.name = "CalibrationUnitThread"
        self._labjack = None
        self._data_table_name = "CalibrationUnit"

        # lower numbers are higher priority
        # task priority is *also* used to identify tasks later, so that
        # pending cal and background can be cancelled by the user
        self._calibration_tasks_priority = 10
        self._background_tasks_priority = 15
        self._schedule_a_cal_tasks_priority = 20
        self._schedule_a_bg_tasks_priority = 25
        self._measurement_task_priority = 100
        self._connection_task_priority = -1000

        # this special value of labjack_id tells the comms routines not to connect
        if config.kind == "mock":
            labjack_id = None

        self._scheduler.enter(
            delay=0,
            priority=self._connection_task_priority,  # needs to happend before anything else will work
            action=self.connect_to_labjack,
            kwargs={"labjack_id": labjack_id, "serialNumber": serialNumber},
        )

        # ensure that the scheduler function is run immediately on startup
        self.state_changed.set()

    @task_description("Calibration unit: initialize")
    def connect_to_labjack(self, labjack_id, serialNumber):
        with self._lock:
            try:
                self._labjack = CalBoxLabjack(labjack_id, serialNumber=serialNumber)
            except Exception as ex:
                _logger.error(
                    "Unable to connect to calibration system LabJack using "
                    f"ID: {labjack_id} serial: {serialNumber}.  Retrying in 10sec."
                )
                self._scheduler.enter(
                    delay=10,
                    priority=self._connection_task_priority,  # needs to happend before anything else will work
                    action=self.connect_to_labjack,
                    kwargs={"labjack_id": labjack_id, "serialNumber": serialNumber},
                )

    @task_description("Calibration unit: flush source")
    def set_flush_state(self):
        self._datastore.add_log_message(
            "CalibrationEvent", f"Begun flushing radon calibration source"
        )
        self._labjack.flush()

    @task_description("Calibration unit: inject from source")
    def set_inject_state(self):
        self._datastore.add_log_message(
            "CalibrationEvent", f"Begun injecting radon from calibration source"
        )
        # cancel background - so that we are not injecting
        # while flow is turned off (which would lead to a very
        # high radon concentration in the detector)
        self._labjack.reset_background()
        self._labjack.inject()

    @task_description("Calibration unit: switch to background state")
    def set_background_state(self):
        self._datastore.add_log_message("CalibrationEvent", f"Begun background cycle")
        self._labjack.start_background()

    @task_description("Calibration unit: return to idle")
    def set_default_state(self):
        self._datastore.add_log_message(
            "CalibrationEvent", f"Return to normal operation"
        )
        self._labjack.reset_all()

    def set_nonbackground_state(self):
        self._datastore.add_log_message("CalibrationEvent", f"Left background state")
        self._labjack.reset_background()

    def set_noncalibration_state(self):
        self._datastore.add_log_message("CalibrationEvent", f"Left calibration state")
        self._labjack.reset_calibration()

    def measurement_func(self):
        t = datetime.datetime.now(datetime.timezone.utc)
        t = t.replace(microsecond=0)
        data = {"Datetime": t}
        data.update(self._labjack.analogue_states)
        data.update(self._labjack.digital_output_state)
        # send measurement to datastore
        self._datastore.add_record(self._data_table_name, data)

    # don't include this function in the list of tasks
    # @task_description("Calibration unit: measure state")
    def run_measurement(self):
        """call measurement function and schedule next

        If measurement is due at the same time as an action, perform the action first"""
        with self._lock:
            self.measurement_func()
            self._scheduler.enter(
                delay=self.seconds_until_next_measurement,
                priority=self._measurement_task_priority,
                action=self.run_measurement,
            )

    def run_calibration(self, flush_duration, inject_duration, start_time=None):
        """Run the calibration sequence - flush source, inject source

        Parameters
        ----------
        flush_duration : float
            duration of flushing period (sec)
        inject_duration : float
            duration of inject period (sec)
        start_time : datetime.datetie or None, optional
            time when flushing is due to start (UTC), or None (which means to start
            immediately), by default None
        """
        with self._lock:
            _logger.debug(
                f"run_calibration, parameters are flush_duration:{flush_duration}, inject_duration:{inject_duration}, start_time:{start_time}"
            )
            log_start_time = start_time if start_time is not None else "now"
            self._datastore.add_log_message(
                "CalibrationEvent",
                f"Calibration scheduled, start_time: {log_start_time}, flush_duration:{flush_duration}, inject_duration:{inject_duration}, start_time:{start_time}",
            )

            p = self._calibration_tasks_priority
            if start_time is not None:
                initial_delay_seconds = max(
                    0,
                    (
                        start_time - datetime.datetime.now(datetime.timezone.utc)
                    ).total_seconds(),
                )
            else:
                initial_delay_seconds = 0
            #
            # begin flushing
            self._scheduler.enter(
                delay=initial_delay_seconds,
                priority=p,
                action=self.set_flush_state,
            )
            # start calibration *on* the half hour
            #### --- commented out, assume that the calling code will
            #### --- take care of this, and that sometimes users will
            #### --- want to start calibrations right away to see the
            #### --- valves open and close and so forth
            start_on_half_hour = False
            if start_on_half_hour:
                sec_per_30min = 30 * 60
                now = time.time()
                # allow some wiggle room - if flush_duration will take us up to a few seconds past the half
                # hour, just reduce flush_duration by a bit instead of postponing by another half hour
                # this might happen (e.g) if we're starting the job using a task scheduler
                wiggle_room = 10
                delay_inject_start = (
                    next_interval(now + flush_duration - wiggle_room, sec_per_30min)
                    + flush_duration
                    - wiggle_room
                )
            else:
                delay_inject_start = flush_duration

            # start injection
            self._scheduler.enter(
                delay=delay_inject_start,
                priority=p,
                action=self.set_inject_state,
            )

            # stop injection
            delay_inject_stop = delay_inject_start + inject_duration
            self._scheduler.enter(
                delay=delay_inject_stop,
                priority=p,
                action=self.set_default_state,
            )

            self.state_changed.set()

    def run_background(self, duration, start_time=None):
        """Run the calibration sequence - flush source, inject source

        Parameters
        ----------
        duration : float
            duration of background period (sec)
        start_time : datetime.datetime or None, optional
            time when flushing is due to start (UTC), or None (which means to start
            immediately), by default None
        """
        with self._lock:
            log_start_time = start_time if start_time is not None else "now"
            self._datastore.add_log_message(
                "CalibrationEvent",
                f"Background scheduled, start time: {log_start_time}, duration: {duration}",
            )
            p = self._background_tasks_priority
            if start_time is not None:
                initial_delay_seconds = max(
                    0,
                    (
                        start_time - datetime.datetime.now(datetime.timezone.utc)
                    ).total_seconds(),
                )
            else:
                initial_delay_seconds = 0
            #
            # begin background
            self._scheduler.enter(
                delay=initial_delay_seconds,
                priority=p,
                action=self.set_background_state,
            )
            # reset the background flags
            self._scheduler.enter(
                delay=initial_delay_seconds + duration,
                priority=p,
                action=self.set_nonbackground_state,
            )

            self.state_changed.set()

    @task_description("Calibration unit: cancel calibration")
    def cancel_calibration(self):
        """cancel an in-progress calibration and all pending ones"""
        with self._lock:
            self._datastore.add_log_message(
                "CalibrationEvent", f"Cancelling any pending background cycles"
            )
            tasks_to_remove = [
                itm
                for itm in self._scheduler.queue
                if itm.priority == self._calibration_tasks_priority
                or itm.priority == self._schedule_a_cal_tasks_priority
            ]
            for itm in tasks_to_remove:
                self._scheduler.cancel(itm)

            # schedule a task to reset the cal box
            self._scheduler.enter(
                delay=0,
                priority=0,
                action=self.set_noncalibration_state,
            )

            self.state_changed.set()

    @task_description("Calibration unit: schedule recurring calibration")
    def schedule_recurring_calibration(
        self,
        flush_duration: float,
        inject_duration: float,
        first_start_time: datetime.datetime,
        interval: datetime.timedelta,
    ):
        with self._lock:
            # ensure first_start_time is in the future
            now = datetime.datetime.now(datetime.timezone.utc)
            ii = 0
            maxiter = 365 * 2050
            while first_start_time < now:
                first_start_time += interval
                ii += 1
                # try not to hang for ever on bad inputs
                if ii > maxiter:
                    _logger.error(
                        "Unable to schedule recurring calibration (inputs were: flush_duration={inject_duration}, flush_duration={inject_duration}, first_start_time={first_start_time}, interval={interval}"
                    )
                    return
            self.run_calibration(
                flush_duration, inject_duration, start_time=first_start_time
            )
            _logger.info(
                f"Next scheduled calibration (flush: {flush_duration/3600.0}, inject: {inject_duration/3600.} hours) scheduled for {first_start_time} UTC."
            )

            # After the next calibration has completed, schedule the next one
            sched_time = first_start_time + datetime.timedelta(
                seconds=int(flush_duration + inject_duration)
            )
            scheduler_delay_seconds = max(
                0,
                (
                    sched_time - datetime.datetime.now(datetime.timezone.utc)
                ).total_seconds(),
            )
            self._scheduler.enter(
                delay=scheduler_delay_seconds,
                priority=self._schedule_a_cal_tasks_priority,
                action=self.schedule_recurring_calibration,
                argument=(flush_duration, inject_duration, first_start_time, interval),
            )

    @task_description("Calibration unit: schedule recurring background")
    def schedule_recurring_background(
        self,
        duration: float,
        first_start_time: datetime.datetime,
        interval: datetime.timedelta,
    ):
        with self._lock:
            # ensure first_start_time is in the future
            now = datetime.datetime.now(datetime.timezone.utc)
            ii = 0
            maxiter = 365 * 2050
            while first_start_time < now:
                first_start_time += interval
                ii += 1
                # try not to hang for ever on bad inputs
                if ii > maxiter:
                    _logger.error(
                        "Unable to schedule recurring background (inputs were: duration={duration}, first_start_time={first_start_time}, interval={interval}"
                    )
                    return

            self.run_background(duration, start_time=first_start_time)
            _logger.info(
                f"Next scheduled background ({duration/3600.0} hours) scheduled for {first_start_time} UTC."
            )

            # After the next background has completed, schedule the next one
            sched_time = first_start_time + datetime.timedelta(seconds=int(duration))
            scheduler_delay_seconds = max(
                0,
                (
                    sched_time - datetime.datetime.now(datetime.timezone.utc)
                ).total_seconds(),
            )
            self._scheduler.enter(
                delay=scheduler_delay_seconds,
                priority=self._schedule_a_bg_tasks_priority,
                action=self.schedule_recurring_background,
                argument=(duration, first_start_time, interval),
            )

    @task_description("Calibration unit: cancel background")
    def cancel_background(self):
        """cancel an in-progress background and all pending ones"""
        with self._lock:
            self._datastore.add_log_message(
                "CalibrationEvent", f"Cancelling any pending calibration cycles"
            )
            tasks_to_remove = [
                itm
                for itm in self._scheduler.queue
                if itm.priority == self._background_tasks_priority
                or itm.priority == self._schedule_a_bg_tasks_priority
            ]
            for itm in tasks_to_remove:
                self._scheduler.cancel(itm)

            # schedule a task to reset the cal box
            self._scheduler.enter(
                delay=0,
                priority=0,
                action=self.set_nonbackground_state,
            )

            self.state_changed.set()

    @property
    def status(self):
        if self._labjack is None:
            status = {}
            status["message"] = "no connection"
        else:
            status = self._labjack.status

        return status

    def cal_and_bg_is_scheduled(self):
        """return true if it looks like a bg and cal are scheduled"""
        with self._lock:
            scheduled_cal_bg_tasks = [
                itm
                for itm in self._scheduler.queue
                if itm.priority == self._schedule_a_bg_tasks_priority
                or itm.priority == self._schedule_a_cal_tasks_priority
            ]
        n = len(scheduled_cal_bg_tasks)
        if n == 1 or n > 2:
            _logger.warning(
                f"Unexpected number of scheduled background & calibration tasks ({n}) - the scheduler may be in an inconsistent state"
            )
        return n >= 2


def fix_record(record: Dict):
    """fix a record from cr1000"""
    r = {}
    for k, v in record.items():
        # work around (possible but not observed) problem
        # of bytes being used as key
        try:
            new_k = k.decode()
        except (UnicodeDecodeError, AttributeError):
            new_k = str(k)
        # work around problem of cr1000 converting to strings like
        # "b'RelHum_Avg'"
        if k.startswith("b'") and k.endswith("'"):
            new_k = k[2:-1]
        r[new_k] = v
        # Define the timestamp as utc
        if k == "Datetime":
            r[k] = r[k].replace(tzinfo=datetime.timezone.utc)
    return r


class DataLoggerThread(DataThread):
    def __init__(self, detector_config, *args, **kwargs):
        # TODO: include type annotations
        super().__init__(*args, **kwargs)
        self.measurement_interval: int = 5  # TODO: from config?, this is in seconds
        self._config = detector_config
        self._datalogger = None
        self.status = {"link": "connecting", "serial": None}
        self.name = "DataLoggerThread"
        self.detectorName = detector_config.name
        self.tables = []
        # set this to a long time ago
        self._last_time_check = datetime.datetime.min
        # buffer for last 30 minutes of 10-second (RTV) measurements
        self._rtv_buffer = collections.deque(maxlen=30 * 6)

        self._scheduler.enter(
            delay=0,
            priority=-1000,  # needs to happend before anything else will work
            action=self.connect_to_datalogger,
            kwargs={"detector_config": detector_config},
        )

        # ensure that the scheduler function is run immediately on startup
        self.state_changed.set()

    def _connect(self, detector_config):
        self._datalogger: CR1000 = CR1000.from_url(
            detector_config.serial_port, timeout=2
        )

    @task_description("Data logger: initialize")
    def connect_to_datalogger(self, detector_config):
        with self._lock:
            self._connect(detector_config)
            # TODO: handle 'unable to connect' error
            self.tables = [str(itm, "ascii") for itm in self._datalogger.list_tables()]
            # Filter the tables - only include the ones which are useful
            tables_to_use = ["Results", "RTV"]
            self.tables = [itm for itm in self.tables if itm in tables_to_use]
            
            self.status["link"] = "connected"
            self.status["serial"] = int(self._datalogger.getprogstat()["SerialNbr"])
            if not detector_config.datalogger_serial == -1:
                if not self.status["serial"] == detector_config.datalogger_serial:
                    _logger.error(
                        "Datalogger found, but serial number does not match configuration (required serial: {datalogger_config.serial}, discovered serial: {self.status['serial'] }"
                    )
                    self._datalogger.close()
                    self.status["link"] = "disconnected"
                    # TODO: the user needs to be informed of this more clearly

            if hasattr(self._datalogger.pakbus.link, "baudrate"):
                _logger.info(
                    f"Connected to datalogger (serial {self.status['serial']}) using serial port, baudrate: {self._datalogger.pakbus.link.baudrate}"
                )

            # set this to a long time ago
            self._last_time_check = datetime.datetime.min.replace(
                tzinfo=datetime.timezone.utc
            )

    def measurement_func(self):
        # TODO: handle lost connection
        self.status["link"] = "retrieving data"
        with self._lock:
            for table_name in self.tables:
                # it's possible to send data from each datalogger to a separate table.
                # destination_table_name = self._config.name + "_" + table_name
                destination_table_name = table_name
                update_time = self._datastore.get_update_time(
                    destination_table_name, self.detectorName
                )
                if update_time is not None:
                    update_time += datetime.timedelta(seconds=1)
                # The get_data_generator function doesn't like timezones
                if update_time is not None:
                    update_time = update_time.replace(tzinfo=None)

                total_num_records = 0
                for data in self._datalogger.get_data_generator(
                    table_name, start_date=update_time
                ):
                    # return early if another task is trying to execute
                    # (likely this is a shutdown request)
                    if self.state_changed.is_set():
                        return
                    # it is Ok for this to take a long time to run - datalogger is slow
                    # Note: I considered breaking out of the loop early after e.g. 5 seconds so that the other
                    # tables get updated too, but that causes problems in the data archive code
                    self.update_heartbeat_time()
                    if len(data) > 0:
                        total_num_records += len(data)
                        msg = f"Received data ({total_num_records} records) from table {destination_table_name} with start_date = {update_time}."
                        _logger.debug(msg)
                        self.status["link"] = msg


                        for itm in data:
                            itm = fix_record(itm)
                            itm["DetectorName"] = self._config.name
                            self._datastore.add_record(destination_table_name, itm)
                            if table_name == "RTV":
                                self._rtv_buffer.append(itm)
        self.status["link"] = "connected"

        # include the clock check as part of the measurement function
        if datetime.datetime.now(
            datetime.timezone.utc
        ) - self._last_time_check > datetime.timedelta(days=15):
            self.synchronise_clock()
            self.log_status()
            self._last_time_check = datetime.datetime.now(datetime.timezone.utc)

    def html_current_status(self):
        """Return the current measurement status as html"""
        info = {
            "var": ["LLD", "ULD", "HV", "InFlow", "ExFlow", "AirT", "RelHum", "Pres"],
            "description": [
                "Total Counts",
                "Noise Counts",
                "PMT Voltage",
                "Internal Flow Velocity",
                "External Flow Rate",
                "Air Temperature",
                "Relative Humidity",
                "Pressure",
            ],
            "units": [
                "Last 30 minutes",
                "Last 30 minutes",
                "V",
                "m/s",
                "L/min",
                "deg C",
                "%",
                "hPa",
            ],
        }
        nvar = len(info["var"])

        if len(self._rtv_buffer) == 0:
            values = ["---"] * nvar
        else:
            recent_data = self._rtv_buffer[-1]
            data_age = (
                datetime.datetime.now(datetime.timezone.utc) - recent_data["Datetime"]
            )
            # don't show values if logging seems to be interrupted
            if data_age > datetime.timedelta(seconds=60):
                values = ["---"] * nvar
            else:
                # don't yet have 30 minutes of data
                if len(self._rtv_buffer) < self._rtv_buffer.maxlen:
                    values = ["wait", "wait"]
                else:
                    time_span = (
                        self._rtv_buffer[-1]["Datetime"]
                        - self._rtv_buffer[0]["Datetime"]
                    )
                    if not time_span == datetime.timedelta(minutes=29, seconds=50):
                        # the buffer is the correct length, but it covers the wrong period
                        # (logging might have been interrupted)

                        values = ["wait2", "wait2"]
                    else:
                        lld_total = sum([itm["LLD"] for itm in self._rtv_buffer])
                        uld_total = sum([itm["ULD"] for itm in self._rtv_buffer])
                        values = [lld_total, uld_total]
                # other values are just taken from the most recent info
                values = values + [recent_data.get(k, "---") for k in info["var"][2:]]
                # pressure, convert from Pa to hPa
                values[-1] = round(values[-1] / 100.0, 1)
                values = [str(itm) for itm in values]
        info["values"] = values
        title = self.detectorName + " Radon Detector"
        html = status_as_html(title, info)
        return html

    def log_status(self):
        progstat = self._datalogger.getprogstat()
        self._datastore.add_log_message(
            "LoggerStatusCheck",
            f"Detector: {self.detectorName}, {pprint.pformat(progstat)}",
        )
        # TODO: work out which file is running from progstat
        fname = str(progstat['ProgName'], 'utf-8')
        data_file = str(self._datalogger.getfile(fname), 'utf-8')
        self._datastore.add_log_message(
            "LoggerFirmware", f"Detector: {self.detectorName}, \n{data_file}"
        )

    def get_clock_offset(self):
        """
        return datalogger time minus computer time, in seconds, as well
        as 1/2 the time it took to query the datalogger
        """
        # measure the length of time required to query the datalogger clock
        # -- first query it, in case of slow response due to power saving
        # -- mode or some such
        t_datalogger = self._datalogger.gettime().replace(tzinfo=datetime.timezone.utc)
        tick = time.time()
        t_datalogger = self._datalogger.gettime().replace(tzinfo=datetime.timezone.utc)
        t_computer = datetime.datetime.now(datetime.timezone.utc)
        tock = time.time()
        time_required_for_query = tock - tick
        halfquery = datetime.timedelta(seconds=time_required_for_query / 2.0)
        # estimate that the actual time on the datalogger probably happend
        # a short time ago
        t_datalogger = t_datalogger - halfquery
        clock_offset = (t_datalogger - t_computer).total_seconds()

        return clock_offset, halfquery

    def synchronise_clock(
        self, maximum_time_difference_seconds=60, check_ntp_sync=True
    ):
        """Attempt to synchronise the clock on the datalogger with computer."""
        # NOTE: the api for adjusting the datalogger clock isn't accurate beyond 1 second
        # TODO: maybe improve this situation
        minimum_time_difference_seconds = 1
        # TODO: check that the computer time is reliable, i.e. NTP sync
        #
        ntp_sync_ok = "unknown"  # TODO: flag this as true or false
        clock_offset, halfquery = self.get_clock_offset()
        self._datastore.add_log_message(
            "ClockCheck",
            f"Computer synced with network time: {ntp_sync_ok}, time difference (datalogger minus computer): {clock_offset}, detector: {self.detectorName}",
        )
        if (
            maximum_time_difference_seconds is not None
            and clock_offset > maximum_time_difference_seconds
        ):
            # don't touch the clock - something is amiss
            _logger.error(
                f"Datalogger and computer clocks are out of synchronisation by more than {maximum_time_difference_seconds} seconds, not adjusting time"
            )
        elif (
            maximum_time_difference_seconds is not None
            and clock_offset < minimum_time_difference_seconds
        ):
            _logger.info(
                f"Datalogger and computer clocks are out of synchronisation by less than {minimum_time_difference_seconds} seconds, not adjusting time"
            )
        else:
            new_time = datetime.datetime.now(datetime.timezone.utc) + halfquery
            self._datalogger.settime(new_time)
            clock_offset, halfquery = self.get_clock_offset()
            self._datastore.add_log_message(
                "ClockCheck",
                f"Synchronised datalogger clock with computer clock, time difference (datalogger minus computer): {clock_offset}, detector: {self.detectorName}",
            )


class MockCR1000(object):
    """
    This object simulates some of the CR1000 interface to permit testing the rest of the code
    """

    class PakBus:
        link = {"baudrate": 42}

    pakbus = PakBus()

    def __init__(self, *args, **kwargs):
        # for faking a clock offset
        self.__timeoffset = datetime.timedelta(seconds=3)
        self._rec_nbr = {"RTV": 0, "Results": 0}
        pass

    def list_tables(self):
        return [b"Results", b"RTV"]

    def gettime(self):
        time.sleep(0.01)
        # this returns a timezone naive object, to match
        # the CR1000 library
        t = datetime.datetime.utcnow() + self.__timeoffset
        t = t.replace(microsecond=0)
        time.sleep(0.01)
        return t

    def settime(self, t):
        time.sleep(0.01)
        self.__timeoffset = datetime.datetime.now(datetime.timezone.utc) - t
        time.sleep(0.01)

    def getprogstat(self):
        return {"SerialNbr": "42", "Kind": "MOCK"}

    def getfile(self, fname):
        data = f"this is some file data\n\nFilename requested was: {fname}".encode(
            "ascii"
        )
        return data

    def close(self):
        pass

    def get_data_generator(self, table_name, start_date):
        """define some mock data which looks like it came from a datalogger

        This behaves in a similar way to CR1000.get_data_generator
        """
        # number of records to return at once
        # Database is good with 1440 * 6, but if we
        # plan to query the rowid column later it's better to keep
        # the batchsize smaller
        batchsize = 1440 * 6

        # an arbitrary reference time
        tref = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
        # number of days back in time to generate data for
        # (need more than 60 to test rollover functions)
        numdays = 100
        t_latest = datetime.datetime.now(datetime.timezone.utc)

        if table_name == "RTV":
            # rtv contains data at each 10 seconds
            t_latest = t_latest.replace(
                microsecond=0, second=t_latest.second // 10 * 10
            )
            dt = datetime.timedelta(seconds=10)
            numrecs = 8640 * numdays
        elif table_name == "Results":
            t_latest = t_latest.replace(
                microsecond=0, second=0, minute=t_latest.minute // 30 * 30
            )
            dt = datetime.timedelta(minutes=30)
            numrecs = numdays * 24 * 2

        # if start date has been provided, use that for numrecs instead (limited to a maximum of numrecs)
        if start_date is not None:
            numrecs = min(
                numrecs,
                int((t_latest - start_date).total_seconds() // dt.total_seconds()) + 1,
            )

        recs_to_return = []

        def rn_func(t):
            rn = 200.0 + 100.0 * np.sin(
                (t - tref).total_seconds() * 2 * np.pi / (3600 * 24)
            )
            source_injection = True
            if source_injection:
                rn *= 50
            return rn

        rng = np.random.default_rng()

        for ii in reversed(range(numrecs)):
            if table_name == "RTV":
                t = t_latest - ii * dt
                rec_num = int((t - tref).total_seconds() / dt.total_seconds())
                itm = {
                    "Datetime": t,
                    "RecNbr": rec_num,
                    "ExFlow": 80.01,
                    "InFlow": 11.1,
                    "LLD": rng.poisson(rn_func(t) / 6.0 / 30.0),
                    "ULD": 0,
                    "Pres": 101325.01,
                    "TankP": 100.01,
                    "HV": 980.5,
                    "RelHum": 80.5,
                }
            elif table_name == "Results":
                t = t_latest - ii * dt
                self._rec_nbr["Results"] += 1
                rec_num = int((t - tref).total_seconds() / dt.total_seconds())
                itm = {
                    "Datetime": t,
                    "RecNbr": rec_num,
                    "ExFlow_Tot": 0.0,
                    "InFlow_Avg": -13.84,
                    "LLD_Tot": rng.poisson(rn_func(t)),
                    "ULD_Tot": 0.0,
                    "Gas_meter_Tot": 0.0,
                    "AirT_Avg": -168.9,
                    "RelHum_Avg": 34.86,
                    "TankP_Avg": -558.7,
                    "Pres_Avg": 419.6658020019531,
                    "HV_Avg": -712.7,
                    "PanTemp_Avg": 21.26,
                    "BatV_Avg": 15.24,
                }

            if start_date is None or t >= start_date:
                recs_to_return.append(itm)
                if len(recs_to_return) >= batchsize:
                    yield recs_to_return
                    recs_to_return = []
        if len(recs_to_return) > 0:
            yield recs_to_return


class MockDataLoggerThread(DataLoggerThread):
    def __init__(self, detector_config, *args, **kwargs):
        super().__init__(detector_config, *args, **kwargs)

    def _connect(self, detector_config):
        time.sleep(4)  # simulate delay for comms
        self._datalogger = MockCR1000()
        _logger.warning("*** Pretend connection to a datalogger ***")


class DataMinderThread(DataThread):
    """
    This thread's job is to perform some maintainence tasks on the database

    * database backups
    * sync Results table to legacy-format csv files
    * ...

    These should be carried out periodically (depending on settings) or on-demand

    """

    def __init__(self, config: Configuration, *args, **kwargs):
        # TODO: include type annotations
        super().__init__(*args, **kwargs)
        self.measurement_interval: int = 5  # TODO: from config?, this is in seconds
        self._config = config
        self._datalogger = None
        self.status = "Idle"
        self.name = "DataMinderThread"

        self._backup_lock = threading.RLock()
        self._csv_output_lock = threading.RLock()

        # perform some tasks a short time after startup
        # TODO: obtain backup time from configuration file
        backup_time_of_day = datetime.time(0, 10)
        delay_seconds = 10 * 60
        self._scheduler.enter(
            delay=delay_seconds,
            priority=0,
            action=self.run_database_tasks,
            kwargs={"backup_time_of_day": backup_time_of_day},
        )

        ## for debugging - print backtrace of all threads
        # self._scheduler.enter(
        #        delay=30,
        #        priority=0,
        #        action=log_backtrace_all_threads,
        #        kwargs={},
        #    )

        # ensure that the scheduler function is run immediately on startup
        self.state_changed.set()

    def backup_active_database(self, backup_filename=None):
        with self._backup_lock:
            self._datastore.backup_active_database(backup_filename)

    def archive_data(self, data_dir):
        with self._backup_lock:
            _logger.debug(f"Archiving old records from active database")
            self._datastore.archive_data(data_dir=self._config.data_dir)

    def sync_legacy_files(self, data_dir):
        with self._csv_output_lock:
            _logger.debug("Writing data to legacy file format")
            self._datastore.sync_legacy_files(data_dir)

    def run_database_tasks(self, backup_time_of_day: datetime.time):
        # there may be a long delay (e.g. network drives), so allow
        # this routine to hang without bringing down the entire program
        with self._heartbeat_time_lock:
            self._tolerate_hang = True

        # sleep here allows other database threads (which may be scheduled on the minute)
        # to have a chance to run first
        time.sleep(1)
        t0 = datetime.datetime.now(datetime.timezone.utc)
        # run tasks
        self.sync_legacy_files(data_dir=self._config.data_dir)
        self.archive_data(data_dir=self._config.data_dir)
        self.backup_active_database()
        t = datetime.datetime.now(datetime.timezone.utc)
        _logger.info(f"Database backup, archive, and legacy file export took {t-t0}")

        # re-schedule next backup
        next_backup = datetime.datetime.combine(t.date(), backup_time_of_day).replace(
            tzinfo=datetime.timezone.utc
        )
        if (next_backup - t).total_seconds() < 60:
            next_backup += datetime.timedelta(days=1)
        delay_seconds = (next_backup - t).total_seconds()

        _logger.info(
            f"Next backup scheduled for {next_backup} in {delay_seconds/3600:.03} hours"
        )

        self._scheduler.enter(
            delay=delay_seconds,
            priority=0,
            action=self.run_database_tasks,
            kwargs={"backup_time_of_day": backup_time_of_day},
        )

        self.update_heartbeat_time()
        with self._heartbeat_time_lock:
            self._tolerate_hang = True
