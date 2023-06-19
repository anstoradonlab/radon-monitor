import collections
import copy
import datetime
import ftplib
import functools
import json
import logging
import math
import pathlib
import pprint
import sched
import sys
import threading
import time
import traceback
import typing
from ftplib import FTP
from pathlib import Path
from typing import Dict

import numpy as np
import serial
from pycampbellcr1000 import CR1000
from pycampbellcr1000.utils import ListDict

from ansto_radon_monitor.configuration import Configuration
from ansto_radon_monitor.datastore import DataStore
from ansto_radon_monitor.html import status_as_html

_logger = logging.getLogger()

from .labjack_interface import CalBoxLabjack, CapeGrimLabjack
from .burkert_gateway import BurkertGateway
from .configuration import DetectorConfig


def log_backtrace_all_threads():
    for th in threading.enumerate():
        _logger.error(f"Thread {th}")
        # print(f"Thread {th}", file=sys.stderr)
        msg = "".join(traceback.format_stack(sys._current_frames()[th.ident]))
        _logger.error(f"{msg}")
        # print(f"{msg}", file=sys.stderr)


def approx_tstr(t: datetime.datetime):
    """Return an approximate (truncated to minutes) text representation
       of a datetime.datetime

    Parameters
    ----------
    t : datetime.datetime
        the time to show
    """
    tfmt = "%Y-%m-%d %H:%M%Z"
    return t.strftime(tfmt)


def round_seconds(t: datetime.datetime) -> datetime.datetime:
    """Round a datetime to the nearest second"""
    if t.microsecond >= 500_000:
        t += datetime.timedelta(seconds=1)
    return t.replace(microsecond=0)


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
    sec : float, as e.g. returned by time.time()
        now
    interval : float
        interval length (seconds), > 0.0
    offset : float, optional
        offset for first interval, e.g. if interval is 10.0 and offset is 1.0,
        the interval will expire at 11.0, 21.0, ... sec

    Returns
    -------
    float
        time until next interval expires, guaranteed to be > 0.0 provided that
        interval > 0.0
    """
    t =  (math.ceil((sec - offset) / interval) * interval) - (sec - offset)
    if t == 0:
        # this is more likely to happen if sec comes from a coarse-resolution
        # clock, e.g. time.monotonic is ~15 ms resolution on windows
        # until Python 3.11
        # https://github.com/python-trio/trio/issues/33
        t += interval
    return t


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
        self._last_measurement_time = 0
        self._scheduler = sched.scheduler(time.time, time.sleep)
        self._lock = threading.RLock()
        now = time.time()
        delay = next_interval(now, self.measurement_interval, self.measurement_offset)
        # how long to wait (seconds) before re-connecting.  This delay
        # gets longer on multiple failures
        self._reconnect_delay = 30

        _logger.debug(f"next time: {delay+now} (next - now : {delay})")
        if run_measurement_on_startup:
            delay = 0
        self._scheduler.enter(delay=delay, priority=0, action=self.run_measurement)

        # this is used for detecting a hang
        self._heartbeat_time_lock = threading.RLock()
        self._heartbeat_time = time.time()
        self._tolerate_hang = False
        # maximum time allowed before the thread is assumed to have hung
        self.max_heartbeat_age_seconds = 10

        self._scheduler.enter(delay=1, priority=0, action=self.update_heartbeat_time)

    def shutdown(self):
        self.cancelled = True
        self.state_changed.set()

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

    def reconnect_func(self):
        _logger.debug(f"Reconnect function - stub")

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
        if self.cancelled:
            # do nothing if we're shutting down (especially, don't
            # re-schedule the measurement)
            return
        try:
            self.measurement_func()

        except Exception as ex:
            _logger.error(f"Error while running measurement: {ex}, reconnecting")
            import traceback

            _logger.error(f"{traceback.format_exc()}")
            self.reconnect_func()

        self._scheduler.enter(
            delay=self.seconds_until_next_measurement,
            priority=0,
            action=self.run_measurement,
        )

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
                    # _logger.debug(f"Q: {self._scheduler.queue}")
                    # _logger.debug(f"Task Queue: {self.task_queue}")

            _logger.debug(f"{self.name} has finished and will call shutdown_func()")
            self.shutdown_func()
        except Exception as ex:
            _logger.error(
                f'{self.name} is aborting with an unhandled exception: "{ex}". \n{traceback.format_exc()}\nStack trace for all threads follows.'
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

        labjack_id = config.calbox.labjack_id
        serialNumber = config.calbox.labjack_serial

        # this is the thread which is allowed to access the hardware directly
        self._thread_ident = None
        self._data = None
        self._status_cache = None

        # Labjack API needs None for serialNumber if we are to ignore it
        if serialNumber == -1:
            serialNumber = None

        # initial labjack id/serial number to be used for reconnection
        self._init_labjack_id = labjack_id
        self._init_serialNumber = serialNumber

        # Note: this code is run in the main thread, so avoid doing anything which
        # might block here (instead, add tasks to the scheduler which is called
        # inside )
        super().__init__(datastore, *args, **kwargs)
        self.name = "CalibrationUnitThread"
        self._device = None
        self._data_table_name = "CalibrationUnit"
        self._kind = config.calbox.kind.lower()
        self._num_detectors = len(config.detectors)
        self._detector_names = [itm.name for itm in config.detectors]
        self._radon_source_activity_bq = config.calbox.radon_source_activity_bq
        self._ip_address = config.calbox.me43_ip_address
        self._flush_flow_rate = config.calbox.flush_flow_rate
        self._inject_flow_rate = config.calbox.inject_flow_rate
        self._flow_sensor_polynomial = config.calbox.flow_sensor_polynomial

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
        if config.calbox.kind == "mock":
            labjack_id = None

        self._schedule_connection(
            labjack_id,
            serialNumber,
            self._ip_address,
            self._flush_flow_rate,
            self._inject_flow_rate,
            delay=0,
        )

        # ensure that the scheduler function is run immediately on startup
        self.state_changed.set()

    def _cancel_tasks(self, task_priority):
        for itm in self._scheduler.queue:
            if itm.priority == task_priority:
                self._scheduler.cancel(itm)

    def _schedule_connection(
        self,
        labjack_id,
        serialNumber,
        ip_address="",
        flush_flow_rate=None,
        inject_flow_rate=None,
        delay=10,
    ):
        # cancel any current cal/bg tasks
        self._cancel_tasks(self._calibration_tasks_priority)
        self._cancel_tasks(self._background_tasks_priority)
        self._cancel_tasks(self._connection_task_priority)

        self._device = None
        self._scheduler.enter(
            delay=delay,
            priority=self._connection_task_priority,  # high priority - needs to happend before anything else will work
            action=self.connect_to_device,
            kwargs={
                "labjack_id": labjack_id,
                "serialNumber": serialNumber,
                "ip_address": ip_address,
                "flush_flow_rate": flush_flow_rate,
                "inject_flow_rate": inject_flow_rate,
            },
        )

    @task_description("Calibration unit: initialize")
    def connect_to_device(
        self, labjack_id, serialNumber, ip_address, flush_flow_rate, inject_flow_rate
    ):
        self._thread_ident = threading.get_ident()
        with self._lock:
            try:
                # Note: _kind is set to lower case during __init__
                if self._kind == "mock":
                    self._device = CalBoxLabjack(
                        labjack_id=None, serialNumber=serialNumber
                    )
                elif self._kind == "generic":
                    self._device = CalBoxLabjack(
                        labjack_id,
                        serialNumber=serialNumber,
                        flow_sensor_polynomial=self._flow_sensor_polynomial,
                    )
                elif self._kind == "capegrim":
                    self._device = CapeGrimLabjack(
                        labjack_id,
                        serialNumber=serialNumber,
                        flow_sensor_polynomial=self._flow_sensor_polynomial,
                    )
                elif self._kind == "burkertmodel1":
                    self._device = BurkertGateway(
                        ip_address=ip_address,
                        flush_flow_rate=flush_flow_rate,
                        inject_flow_rate=inject_flow_rate,
                    )
                elif self._kind == "none":
                    self._device = None
                elif self._kind == "mockcapegrim":
                    self._device = CapeGrimLabjack(
                        labjack_id=None, serialNumber=serialNumber
                    )
                else:
                    _logger.error(
                        f"Unknown kind of calibration unit: {self._kind}.  Known kinds are: ['none', 'generic', 'burkertModel1', 'CapeGrim', 'mock', 'mockCapeGrim].  'Mock' kinds are intended for software development only."
                    )
                # no exception - set the reconnect delay to default
                self._reconnect_delay = 30
            except Exception as ex:
                self._reconnect_delay = min(self._reconnect_delay * 2, 1800)
                self._schedule_connection(
                    labjack_id,
                    serialNumber,
                    ip_address=ip_address,
                    flush_flow_rate=flush_flow_rate,
                    inject_flow_rate=inject_flow_rate,
                    delay=self._reconnect_delay,
                )
                if 'burkert' in self._kind.lower():
                    # burkert-based, report ip address info
                    _logger.error(
                        "Unable to connect to calibration system using "
                        f"IP address: {ip_address} because of error: {ex}.  Retrying in {self._reconnect_delay} sec."
                    )
                else:
                    # labjack-based, report labjack info
                    _logger.error(
                        "Unable to connect to calibration system using "
                        f"ID: {labjack_id} serial: {serialNumber} because of error: {ex}.  Retrying in {self._reconnect_delay} sec."
                    )


    @task_description("Calibration unit: flush source")
    def set_flush_state(self):
        try:
            self._device.flush()
            self._datastore.add_log_message(
                "CalibrationEvent", f"Began flushing radon calibration source"
            )
        except Exception as ex:
            _logger.error(
                "Unable set flush state on Labjack "
                f" because of error: {ex}.  Attempting to reconnect and reset in 10sec."
            )
            self._schedule_connection(self._init_labjack_id, self._init_serialNumber)

    def _run_or_reset(self, func, description, argument=()):
        """Run a function, but on failure log the exception and attempt to reconnect to the logger"""
        try:
            func(*argument)
        except Exception as ex:
            _logger.error(
                f"Unable to {description} "
                f" because of error: {ex}.  Attempting to reconnect and reset."
                f"{traceback.format_exc()}"
            )
            self._device = None
            self._schedule_connection(
                self._init_labjack_id,
                self._init_serialNumber,
                self._ip_address,
                self._flush_flow_rate,
                self._inject_flow_rate
            )

    @task_description("Calibration unit: inject from source")
    def set_inject_state(self, detector_idx=0):
        self._datastore.add_log_message(
            "CalibrationEvent",
            f"Began injecting radon from calibration source into detector {detector_idx+1}",
            detector_name=self._detector_names[detector_idx],
        )
        self._run_or_reset(
            self._device.inject, "begin source injection", argument=(detector_idx,)
        )

    @task_description("Calibration unit: switch to background state")
    def set_background_state(self, detector_idx=0):
        self._datastore.add_log_message(
            "CalibrationEvent",
            f"Began background cycle on detector {detector_idx}",
            detector_name=self._detector_names[detector_idx],
        )
        self._run_or_reset(
            self._device.start_background,
            "enter background state",
            argument=(detector_idx,),
        )

    @task_description("Calibration unit: return to idle")
    def set_default_state(self, log_data=None):
        self._datastore.add_log_message(
            "CalibrationEvent", f"Return to normal operation"
        )
        self._run_or_reset(self._device.reset_all, "return to normal operation")
        if log_data is not None:
            json_log_data = json.dumps(log_data, default=str)
            detector_name = log_data.get("DetectorName", None)
            self._datastore.add_log_message(
                "CalibrationEventSummary", json_log_data, detector_name=detector_name
            )

    def set_nonbackground_state(self, log_data=None):
        self._datastore.add_log_message("CalibrationEvent", f"Left background state")
        self._run_or_reset(self._device.reset_background, "leave background state")
        if log_data is not None:
            json_log_data = json.dumps(log_data, default=str)
            detector_name = log_data.get("DetectorName", None)
            self._datastore.add_log_message(
                "CalibrationEventSummary", json_log_data, detector_name=detector_name
            )

    def set_noncalibration_state(self):
        self._datastore.add_log_message("CalibrationEvent", f"Left calibration state")
        self._run_or_reset(self._device.reset_calibration, "leave calibration state")

    def measurement_func(self):
        t = datetime.datetime.now(datetime.timezone.utc)
        t = t.replace(microsecond=0)
        data = {"Datetime": t}
        if self._device is not None:
            data.update(self._device.analogue_states)
            data.update(self._device.digital_output_state)

            # update data cache (for properties)
            self._data = data
            # send measurement to datastore
            self._datastore.add_record(self._data_table_name, data)
            # update the status cache
            _ = self.status

    def shutdown_func(self):
        # this should have no effect.  It's here in case of logic errors in shutdown
        # - a non-logging command to reset the device to its default state.
        if self._device is None:
            return
        try:
            self._device.reset_all()
        except Exception as ex:
            _logger.error(
                f"Error reseting Calbox Device: {ex}, {traceback.format_exc()}"
            )

    # don't include this function in the list of tasks
    # @task_description("Calibration unit: measure state")
    def run_measurement(self):
        """call measurement function and schedule next

        If measurement is due at the same time as an action, perform the action first"""
        with self._lock:
            self._run_or_reset(self.measurement_func, "get Labjack state")
            self._scheduler.enter(
                delay=self.seconds_until_next_measurement,
                priority=self._measurement_task_priority,
                action=self.run_measurement,
            )

    def run_calibration(
        self, flush_duration, inject_duration, start_time=None, detector_idx=0
    ):
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
        detector_idx : int, default 0
            The detector index to target (always 0 for a one-detector setup)
        """
        with self._lock:
            log_start_time = start_time if start_time is not None else "now"
            info_message = (
                f"Calibration scheduled, start_time: {log_start_time}, "
                f"flush_duration:{flush_duration}, "
                f"inject_duration:{inject_duration}, detector: {detector_idx+1}"
            )
            _logger.info(info_message)
            self._datastore.add_log_message(
                "CalibrationEvent",
                info_message,
                detector_name=self._detector_names[detector_idx],
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
            t_inj = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                seconds=initial_delay_seconds
            )
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
                delay_inject_start = flush_duration + initial_delay_seconds

            # start injection
            t0 = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                seconds=delay_inject_start
            )
            info_message = f"Expecting to start injecting radon ({self._detector_names[detector_idx]}) at: {approx_tstr(t0)}"
            _logger.info(info_message)
            self._scheduler.enter(
                delay=delay_inject_start,
                priority=p,
                action=self.set_inject_state,
                argument=(detector_idx,),
            )

            # stop injection
            delay_inject_stop = delay_inject_start + inject_duration
            t1 = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                seconds=delay_inject_stop
            )
            info_message = f"Expecting to stop injecting radon ({self._detector_names[detector_idx]}) at: {approx_tstr(t1)}"
            _logger.info(info_message)

            # if the calibration event is not cancelled, this is the summary metadata which will be
            # written to the database
            calibration_summary = {
                "EventType": "Calibration",
                "FlushStart": round_seconds(t_inj),
                "Start": round_seconds(t0),
                "Stop": round_seconds(t1),
                "DetectorName": self._detector_names[detector_idx],
                "SourceActivity": self._radon_source_activity_bq,
            }

            self._scheduler.enter(
                delay=delay_inject_stop,
                priority=p,
                action=self.set_default_state,
                kwargs={"log_data": calibration_summary},
            )

            self.state_changed.set()

    def run_background(
        self,
        duration: float,
        start_time: datetime.datetime = None,
        detector_idx: int = 0,
    ):
        """Run the calibration sequence - flush source, inject source

        Parameters
        ----------
        duration : float
            duration of background period (sec)
        start_time : datetime.datetime or None, optional
            time when flushing is due to start (UTC), or None (which means to start
            immediately), by default None
        detector_idx : int
            which detector to run the background on (an index, starting from 0)
        """
        with self._lock:
            log_start_time = start_time if start_time is not None else "now"
            self._datastore.add_log_message(
                "CalibrationEvent",
                f"Background scheduled, start time: {log_start_time}, duration: {duration}, detector: {detector_idx+1}",
                detector_name=self._detector_names[detector_idx],
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
            t0 = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                seconds=initial_delay_seconds
            )
            info_message = f"Expecting to start background ({self._detector_names[detector_idx]}) at: {approx_tstr(t0)}"
            _logger.info(info_message)
            self._scheduler.enter(
                delay=initial_delay_seconds,
                priority=p,
                action=self.set_background_state,
                argument=(detector_idx,),
            )
            # reset the background flags
            t1 = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
                seconds=initial_delay_seconds + duration
            )
            info_message = f"Expecting to stop background ({self._detector_names[detector_idx]}) at: {approx_tstr(t1)}"
            # if the calibration event is not cancelled, this is the summary metadata which will be
            # written to the database
            background_summary = {
                "EventType": "Background",
                "Start": round_seconds(t0),
                "Stop": round_seconds(t1),
                "DetectorName": self._detector_names[detector_idx],
            }

            _logger.info(info_message)
            self._scheduler.enter(
                delay=initial_delay_seconds + duration,
                priority=p,
                action=self.set_nonbackground_state,
                kwargs={"log_data": background_summary},
            )

            self.state_changed.set()

    @task_description("Calibration unit: cancel calibration")
    def cancel_calibration(self):
        """cancel an in-progress calibration and all pending ones"""
        with self._lock:
            self._datastore.add_log_message(
                "CalibrationEvent", f"Cancelling calibration cycle"
            )
            self._cancel_tasks(self._calibration_tasks_priority)
            self._cancel_tasks(self._schedule_a_cal_tasks_priority)
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
        detector_idx: int = 0,
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
                flush_duration,
                inject_duration,
                start_time=first_start_time,
                detector_idx=detector_idx,
            )
            _logger.info(
                f"Next scheduled calibration (detector {detector_idx+1}, flush: {flush_duration/3600.0}, inject: {inject_duration/3600.} hours) scheduled for {first_start_time} UTC."
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
                argument=(
                    flush_duration,
                    inject_duration,
                    first_start_time,
                    interval,
                    detector_idx,
                ),
            )

    @task_description("Calibration unit: schedule recurring background")
    def schedule_recurring_background(
        self,
        duration: float,
        first_start_time: datetime.datetime,
        interval: datetime.timedelta,
        detector_idx: int = 0,
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

            self.run_background(
                duration, start_time=first_start_time, detector_idx=detector_idx
            )
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
                argument=(duration, first_start_time, interval, detector_idx),
            )

    @task_description("Calibration unit: cancel background")
    def cancel_background(self):
        """cancel an in-progress background and all pending ones"""
        with self._lock:
            self._datastore.add_log_message(
                "CalibrationEvent", f"Cancelling any pending background cycles"
            )
            self._cancel_tasks(self._background_tasks_priority)
            self._cancel_tasks(self._schedule_a_bg_tasks_priority)
            # schedule a task to reset the cal box
            self._scheduler.enter(
                delay=0,
                priority=0,
                action=self.set_nonbackground_state,
            )
            self.state_changed.set()

    @property
    def status(self):
        if self._device is None:
            status = {}
            status["message"] = "no connection"
        else:
            if threading.get_ident() == self._thread_ident:
                status = self._device.status
                self._status_cache = status
            else:
                # use the cache if we are not inside the thread
                # which is permitted to talk to the hardware
                status = self._status_cache
                if status is None:
                    status = {}
                    status["message"] = "no connection"

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
        expected_num_tasks = self._num_detectors * 2
        if not n == expected_num_tasks:
            _logger.warning(
                f"Unexpected number of scheduled background & calibration tasks ({n}, expected {expected_num_tasks}) - the scheduler may be in an inconsistent state"
            )
        return n >= expected_num_tasks

    @property
    def cal_running(self):
        """True if a calibration is currently underway"""
        with self._lock:
            for task in self._scheduler.queue:
                if task.priority == self._calibration_tasks_priority:
                    return True
        return False

    @property
    def bg_running(self):
        """True if a background is currently underway"""
        with self._lock:
            for task in self._scheduler.queue:
                if task.priority == self._background_tasks_priority:
                    return True
        return False


def fix_record(
    record: Dict, time_offset: datetime.timedelta = datetime.timedelta(seconds=0)
):
    """fix a record from cr1000

    Parameters
    ----------
    record : Dict
        Data record
    time_offset : datetime.timedelta, optional
        Time offset, subtracted from record, by default datetime.timedelta(seconds=0)

    Returns
    -------
    Dict
        Data record, with time offset removed, timezone info added, and
        some "Bytes" issues fixed
    """
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
        # Define the timestamp as utc and subtract offset
        if k == "Datetime":
            r[k] = r[k].replace(tzinfo=datetime.timezone.utc) - time_offset
    # special case, multiple head detector fields like LLD(1), LLD(2), ...
    if "HV(1)" in r.keys() or "HV_Avg(1)" in r.keys():
        if "HV_Avg(1)" in r.keys():
            suffix_av = "_Avg"
            suffix_tot = "_Tot"
        else:
            suffix_av = ""
            suffix_tot = ""
        try:
            k_summary = "LLD" + suffix_tot
            if not k_summary in r:
                cols = [k for k in r if k.startswith("LLD") and k.endswith(")")]
                if len(cols) > 0:
                    r[k_summary] = np.sum([r[k] for k in cols])
            k_summary = "ULD" + suffix_tot
            if not k_summary in r:
                cols = [k for k in r if k.startswith("ULD") and k.endswith(")")]
                if len(cols) > 0:
                    r[k_summary] = np.sum([r[k] for k in cols])
            k_summary = "HV" + suffix_av
            if not k_summary in r:
                cols = [k for k in r if k.startswith("HV") and k.endswith(")")]
                if len(cols) > 0:
                    r[k_summary] = np.mean([r[k] for k in cols])
            k_summary = "InFlow" + suffix_av
            if not k_summary in r:
                cols = [k for k in r if k.startswith("InFl") and k.endswith(")")]
                if len(cols) > 0:
                    r[k_summary] = np.mean([r[k] for k in cols])
        except Exception as ex:
            _logger.error(
                f"Error adding summary information to record.  Data: {record}, Error: {ex}"
            )

    if "HV(1)" in r.keys() or "HV_Avg(1)" in r.keys():
        # rename HV(1) etc to HV1, HV2
        new_r = {}
        for k, v in r.items():
            new_k = k.replace("(", "").replace(")", "")
            new_r[new_k] = v
        r = new_r

    return r


class DataLoggerThread(DataThread):
    def __init__(self, detector_config: DetectorConfig, *args, **kwargs):
        # TODO: include type annotations
        super().__init__(*args, **kwargs)
        self.measurement_interval: int = 5  # TODO: from config?, this is in seconds
        # a list of tables which are to be read from the datalogger (if present)
        self._tables_to_use = ["Results", "RTV", "HURD2OUT"]
        # Rename certain tables
        # use like this:
        #  {"NAME_ON_DATALOGGER": "NAME_IN_DATABASE"}
        self._rename_table = {"HURD2OUT": "Results"}
        self._config = detector_config
        self._datalogger: typing.Optional[CR1000] = None
        self._last_stats_report_hour = None
        self.status = {"link": "connecting", "serial": None}
        self.name = f"DataLoggerThread({detector_config.name})"
        self.detectorName = detector_config.name
        self.tables: typing.List[str] = []
        # set this to a long time ago
        self._last_time_check = datetime.datetime.min
        # buffer for last 30 minutes of 10-second (RTV) measurements
        self._rtv_buffer: collections.deque = collections.deque(maxlen=30 * 6)
        self._fill_rtv_buffer()

        self._scheduler.enter(
            delay=0,
            priority=-1000,  # needs to happend before anything else will work
            action=self.connect_to_datalogger,
            kwargs={"detector_config": detector_config},
        )

        # set default values for cal and bg coefficients in persistent state
        detector_volumes = {"L100": 0.1, "L200": 0.2, "L1500": 1.5, "L5000": 5.0}
        detector_volume = detector_volumes.get(detector_config.kind, 1.0)
        default_cal = 0.2 * detector_volume
        default_bg_cps = (
            100.0 / 30.0 / 60.0 * 7
            if detector_config.kind == "L5000"
            else 100.0 / 30.0 / 60.0
        )
        k = self.detectorName + " sensitivity"
        cal = self._datastore.get_state(k)
        if cal is None:
            self._datastore.set_state(k, default_cal)
        k = self.detectorName + " background cps"
        bg = self._datastore.get_state(k)
        if bg is None:
            self._datastore.set_state(k, default_bg_cps)

        # ensure that the scheduler function is run immediately on startup
        self.state_changed.set()

    def _connect(self, detector_config):
        # don't use from_url ref:
        # https://github.com/LionelDarras/PyCampbellCR1000/issues/21#issuecomment-1117096281
        # use port=None to create a serial port object without opening the underlying port
        ser = serial.Serial(
            port=None,
            baudrate=detector_config.baudrate,
            timeout=2,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=1,
        )
        ser.port = detector_config.serial_port
        self._datalogger = CR1000(ser)
        # use a fairly short timeout during the connection process (because one of the steps involves
        # reading from the port until timeout to clear the buffers) but then change the timeout
        # to a larger value once connected
        ser.timeout = 4
        # on one of the serial-to-usb drivers that I've used, it seems to be a bad idea to read from
        # the port right after changing the timeout - add a delay here to (hopefully) avoid this
        # issue
        time.sleep(0.25)

    def _fill_rtv_buffer(self):
        """
        attempt to fill the rtv buffer from values in the database

        This would be helpful if the user stops logging then re-starts
        almost immediately
        (perhaps after making a configuration change)
        """
        try:
            table_name = "RTV"
            if not table_name in self._datastore.tables:
                return

            halfhour = datetime.timedelta(minutes=30)
            start_time = datetime.datetime.now(tz=datetime.timezone.utc) - halfhour
            _, data = self._datastore.get_rows(table_name, start_time)
            data = [itm for itm in data if itm["DetectorName"] == self.detectorName]
            for itm in data:
                self._rtv_buffer.append(itm)
        except Exception as ex:
            s = f"Error loading RTV from database (data display may show invalid data for the next 30 minutes): {ex} "
            s += traceback.format_exc()
            _logger.error(s)

    def _report_pakbus_stats(self, force=False):
        """report pakbus packet statistics to logger.info hourly

        Args:
            force (bool, optional):
            Force output of statistics, even if the hour isn't up. Defaults to False.
        """
        # datalogger not connected
        if self._datalogger is None:
            return
        # datalogger doesn't support stats
        if not hasattr(self._datalogger.pakbus, "stats"):
            return
        # configuration file says not to report statistics
        if not self._config.report_pakbus_statistics:
            return
        # check that an hour has rolled over
        if not force:
            current_hour = datetime.datetime.utcnow().hour
            if self._last_stats_report_hour == current_hour:
                return
            self._last_stats_report_hour = current_hour
        # do it
        report_txt = self._datalogger.pakbus.stats.summary()
        self._datalogger.pakbus.stats.reset()
        _logger.info(report_txt)

    def shutdown_func(self):
        # the CR1000 finalizer (__del__) closes the port and
        # sends a goodbye message to the datalogger.  It is
        # an 'implementation detail' of Cython that this will
        # happen right away
        self._report_pakbus_stats(force=True)
        self._datalogger = None

    def reconnect_func(self):
        """This gets called if 'measurement_func' fails"""
        if self._datalogger is not None:
            self._report_pakbus_stats(force=True)
            device = self._datalogger
            self._datalogger = None
            try:
                if hasattr(device.pakbus.link, "_serial"):
                    # connection is using a pylink object
                    device.pakbus.link._serial.close()
                elif hasattr(device.pakbus.link, "close"):
                    # connection is using a pyserial object
                    device.pakbus.link.close()

            except Exception as ex:
                _logger.error(f"Error while trying to close serial port: {ex}")

        self._scheduler.enter(
            delay=0,
            priority=-1000,  # needs to happend before anything else will work
            action=self.connect_to_datalogger,
            kwargs={"detector_config": self._config},
        )

        # Simulated error
        # import random
        # if random.random() > 0.5:
        #    raise RuntimeError("Pretend error during re-connection")

    @task_description("Data logger: initialize")
    def connect_to_datalogger(self, detector_config):
        try:
            with self._lock:
                self.status["link"] = "connecting to datalogger"
                try:
                    self._connect(detector_config)
                    # on success, reset reconnect delay
                    self._reconnect_delay = 30
                except Exception as ex:
                    _logger.error(
                        "Unable to connect to data logger "
                        f"config: {detector_config} because of error: {ex}.  Retrying in 30sec."
                    )
                    self._scheduler.enter(
                        delay=self._reconnect_delay,
                        priority=-1000,  # needs to happend before anything else will work
                        action=self.connect_to_datalogger,
                        kwargs={"detector_config": detector_config},
                    )
                    # make re-connect delay longer in case of failure
                    # up to a maximum of 30 minutes
                    self._reconnect_delay = min(self._reconnect_delay * 2, 60*30)
                    return

                # connect can take a long time, but this is Ok
                self._tolerate_hang = True
                self.update_heartbeat_time()
                # TODO: handle 'unable to connect' error
                self.tables = [
                    str(itm, "ascii") for itm in self._datalogger.list_tables()
                ]
                # table discovery can be slow too
                self.update_heartbeat_time()
                # Filter the tables - only include the ones which are useful
                self.tables = [itm for itm in self.tables if itm in self._tables_to_use]

                self.status["link"] = "connected"
                self.status["serial"] = int(self._datalogger.getprogstat()["SerialNbr"])
                if not detector_config.datalogger_serial == -1:
                    if not self.status["serial"] == detector_config.datalogger_serial:
                        _logger.error(
                            f"Datalogger found, but serial number does not match configuration (required serial: {detector_config.serial}, discovered serial: {self.status['serial'] }"
                        )
                        self._datalogger.close()
                        self.status[
                            "link"
                        ] = "disconnected: datalogger has the wrong serial"
                        # TODO: the user needs to be informed of this more clearly

                if hasattr(self._datalogger.pakbus.link, "baudrate"):
                    _logger.info(
                        f"Connected to datalogger (serial {self.status['serial']}) using serial port, baudrate: {self._datalogger.pakbus.link.baudrate}"
                    )

                # set this to a long time ago
                self._last_time_check = datetime.datetime.min.replace(
                    tzinfo=datetime.timezone.utc
                )

        except Exception as ex:
            _logger.error(
                f"Error finalising connection to datalogger: {ex} {traceback.format_exc()}"
            )
            self.reconnect_func()
        finally:
            self._tolerate_hang = False

    def measurement_func(self):
        # if there is not yet a connection, then do nothing
        if self._datalogger is None:
            return

        time_offset = datetime.timedelta(hours=self._config.datalogger_time_offset)

        # TODO: handle lost connection
        self.status["link"] = "retrieving data"
        with self._lock:
            # simulate an intermittent error
            # import random
            # if random.random() > 0.9:
            #    raise RuntimeError("This is not a real error")
            for table_name in self.tables:
                destination_table_name = self._rename_table.get(table_name, table_name)
                # it's possible we might like to send data from each datalogger to a separate table.
                # destination_table_name = self._config.name + "_" + table_name
                update_time = self._datastore.get_update_time(
                    destination_table_name, self.detectorName
                )
                if update_time is not None:
                    # offset a little so that we don't grab the same record again and again
                    update_time += datetime.timedelta(seconds=1)
                    # The get_data_generator function doesn't like timezones
                    update_time = update_time.replace(tzinfo=None)
                    # convert from UTC (all timestamps in database are UTC) into
                    # the datalogger's timezone (usually UTC, but sometimes not)
                    update_time = update_time + time_offset
                total_num_records = 0
                # set stop date to a time in the future (because of the possibility that
                # datalogger timezone doesn't match the computer timezone)
                stop_date = datetime.datetime.utcnow() + datetime.timedelta(days=2)
                for data in self._datalogger.get_data_generator(
                    table_name, start_date=update_time, stop_date=stop_date
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

                        data = [fix_record(itm, time_offset) for itm in data]
                        for itm in data:
                            itm["DetectorName"] = self._config.name
                            if table_name == "RTV":
                                self._rtv_buffer.append(itm)

                        self._datastore.add_records(destination_table_name, data)

        self.status["link"] = "connected"

        # include the clock check as part of the measurement function
        if datetime.datetime.now(
            datetime.timezone.utc
        ) - self._last_time_check > datetime.timedelta(days=15):
            # each of these steps might be slow
            saved_max_hb_age = self.max_heartbeat_age_seconds
            self.max_heartbeat_age_seconds = 300
            try:
                self.synchronise_clock()
                self.log_status()
                self._last_time_check = datetime.datetime.now(datetime.timezone.utc)
            finally:
                self.update_heartbeat_time()
                self.max_heartbeat_age_seconds = saved_max_hb_age

        # This function will only do something when the hour rolls over
        self._report_pakbus_stats()

    def html_current_status(self):
        """Return the current measurement status as html"""
        info = {
            "var": ["LLD", "ULD", "ExFlow", "HV", "InFlow", "AirT", "RelHum", "Pres"],
            "description": [
                "Total Counts",
                "Noise Counts",
                "External Flow Rate",
                "PMT Voltage",
                "Internal Flow Vel.",
                "Air Temperature",
                "Relative Humidity",
                "Pressure",
            ],
            "units": [
                "Last 30 min",
                "Last 30 min",
                "L/min",
                "V",
                "m/s",
                "deg C",
                "%",
                "hPa",
            ],
        }
        nvar = len(info["var"])
        # Exflow needs to be treated similarly to LLD and ULD
        exflow_value = "---"

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
                    values = ["wait", "wait", "wait"]
                else:
                    time_span = (
                        self._rtv_buffer[-1]["Datetime"]
                        - self._rtv_buffer[0]["Datetime"]
                    )
                    if not time_span == datetime.timedelta(minutes=29, seconds=50):
                        # the buffer is the correct length, but it covers the wrong period
                        # (logging might have been interrupted)

                        values = ["wait2", "wait2", "wait2"]
                    else:
                        try:
                            lld_total = sum([itm["LLD"] for itm in self._rtv_buffer])
                        except KeyError:
                            lld_total = "---"
                        try:
                            uld_total = sum([itm["ULD"] for itm in self._rtv_buffer])
                        except KeyError:
                            uld_total = "---"
                        try:
                            exflow_total = sum(
                                [itm["ExFlow"] for itm in self._rtv_buffer]
                            )
                        except KeyError:
                            exflow_total = "---"
                        values = [lld_total, uld_total, exflow_total]

                # other values are just taken from the most recent info
                def converter(k):
                    """return the correct conversion function for key "k" """
                    do_nothing = lambda x: x
                    if (
                        k.startswith("LLD")
                        or k.startswith("ULD")
                        or k.startswith("Press")
                    ):
                        c = int
                    elif (
                        k.startswith("HV")
                        or k.startswith("InFlow")
                        or k.startswith("ExFlow")
                    ):
                        c = lambda x: round(x, 1)
                    else:
                        c = do_nothing
                    return c

                values = values + [recent_data.get(k, "---") for k in info["var"][3:]]
                # round-off values, etc
                values_formatted = []
                for k, v in zip(info["var"], values):
                    try:
                        cv = converter(k)(v)
                    except:
                        cv = v
                    values_formatted.append(cv)

                # pressure, convert from Pa to hPa
                ### - no, this conversion happens already
                ### values[-1] = round(values[-1] / 100.0, 1)
                values = [str(itm) for itm in values_formatted]
        info["values"] = values
        title = self.detectorName + " Radon Detector"
        html = status_as_html(title, info)
        return html

    def log_status(self):
        progstat = self._datalogger.getprogstat()
        self._datastore.add_log_message(
            "LoggerStatusCheck",
            f"Detector: {self.detectorName}, {pprint.pformat(progstat)}",
            detector_name=self.detectorName,
        )
        fname = str(progstat["ProgName"], "utf-8")
        data_file = str(self._datalogger.getfile(fname), "utf-8")
        self._datastore.add_log_message(
            "LoggerFirmware",
            f"Detector: {self.detectorName}, \n{data_file}",
            detector_name=self.detectorName,
        )

    def get_clock_offset(self):
        """
        return datalogger time minus computer time, in seconds, as well
        as 1/2 the time it took to query the datalogger
        """
        time_offset = datetime.timedelta(hours=self._config.datalogger_time_offset)
        # measure the length of time required to query the datalogger clock
        # -- first query it, in case of slow response due to power saving
        # -- mode or some such
        t_datalogger = (
            self._datalogger.gettime().replace(tzinfo=datetime.timezone.utc)
            - time_offset
        )
        tick = time.time()
        t_datalogger = (
            self._datalogger.gettime().replace(tzinfo=datetime.timezone.utc)
            - time_offset
        )
        t_computer = datetime.datetime.now(datetime.timezone.utc)
        tock = time.time()
        time_required_for_query = tock - tick
        halfquery = datetime.timedelta(seconds=time_required_for_query / 2.0)
        # estimate that the actual time on the datalogger probably happend
        # a short time ago
        t_datalogger = t_datalogger - halfquery
        clock_offset = (t_datalogger - t_computer).total_seconds()

        return clock_offset, halfquery

    def increment_datalogger_clock(self, increment_dt: float):
        """
        Adjust time by adding "increment_dt" seconds
        """
        if self._datalogger is None:
            return
        increment_seconds = int(increment_dt)
        increment_nanoseconds = int((increment_dt - increment_seconds) * 1e9)
        if not hasattr(self._datalogger.pakbus, "get_clock_cmd"):
            # Handle the case where this is not a real datalogger
            t = self._datalogger.gettime()
            t += datetime.timedelta(seconds=increment_dt)
            self._datalogger.settime(t)
        else:
            self._datalogger.pakbus.get_clock_cmd(
                (increment_seconds, increment_nanoseconds)
            )
            hdr, msg, sdt1 = self._datalogger.send_wait(
                self._datalogger.pakbus.get_clock_cmd(
                    (increment_seconds, increment_nanoseconds)
                )
            )

    def synchronise_clock(
        self, maximum_time_difference_seconds=60, check_ntp_sync=True
    ):
        """Attempt to synchronise the clock on the datalogger with computer."""
        # NOTE: the api for adjusting the datalogger clock isn't accurate beyond 1 second
        #       but I'm creating the underlying pakbus messages myself
        #       search for function: increment_datalogger_clock
        minimum_time_difference_seconds = 1
        # TODO: check that the computer time is reliable, i.e. NTP sync
        #       probably use this cross-platform solution https://github.com/cf-natali/ntplib
        #       with a ntp server provided by the configuration
        #       Fallback options are w32tm (windows:    https://superuser.com/questions/425233/how-can-i-check-a-systems-current-ntp-configuration)
        #         ntpstat (Linux), dbus (Linux: https://raspberrypi.stackexchange.com/questions/80219/recommended-way-for-a-python-script-to-check-ntp-update-status-and-initiate-an )

        ntp_sync_ok = "unknown"  # TODO: flag this as true or false
        clock_offset, halfquery = self.get_clock_offset()
        self._datastore.add_log_message(
            "ClockCheck",
            f"Computer synced with network time: {ntp_sync_ok}, time difference (datalogger minus computer): {clock_offset}, detector: {self.detectorName}",
            detector_name=self.detectorName,
        )
        if (
            maximum_time_difference_seconds is not None
            and abs(clock_offset) > maximum_time_difference_seconds
        ):
            # don't touch the clock - something is amiss
            _logger.error(
                f"Datalogger and computer clocks are out of synchronisation by more "
                f"than {maximum_time_difference_seconds} seconds, which is "
                f"unexpected. Time difference (datalogger minus computer) is"
                f": {clock_offset}, detector: {self.detectorName}. Not adjusting "
                f"time (Hint: do the adjustment manually)"
            )
        elif (
            maximum_time_difference_seconds is not None
            and abs(clock_offset) < minimum_time_difference_seconds
        ):
            _logger.info(
                f"Datalogger and computer clocks are synchronised to within {minimum_time_difference_seconds} seconds, not adjusting time (actual difference: {clock_offset} sec)"
            )
        else:
            self.increment_datalogger_clock(-clock_offset)
            clock_offset, halfquery = self.get_clock_offset()
            self._datastore.add_log_message(
                "ClockCheck",
                f"Synchronised datalogger clock with computer clock, time difference (datalogger minus computer): {clock_offset}, detector: {self.detectorName}",
                detector_name=self.detectorName,
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
        self.__timeoffset = datetime.datetime.utcnow() - t
        time.sleep(0.01)

    def getprogstat(self):
        return {
            "SerialNbr": "42",
            "Kind": "MOCK",
            "ProgName": b"Not_a_real_datalogger.cr8",
        }

    def getfile(self, fname):
        data = f"this is some file data\n\nFilename requested was: {fname}".encode(
            "ascii"
        )
        return data

    def close(self):
        pass

    def get_data_generator(self, table_name, start_date, stop_date=None):
        """define some mock data which looks like it came from a datalogger

        This behaves in a similar way to CR1000.get_data_generator
        """
        # handle start_date without timezone
        if start_date is not None:
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=datetime.timezone.utc)
        if stop_date is not None:
            if stop_date.tzinfo is None:
                stop_date = stop_date.replace(tzinfo=datetime.timezone.utc)
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
                    "ExFlow": 80.01 / 6.0 / 30.0,
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
                    "ExFlow_Tot": 80.01,
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
                if stop_date is None or t <= stop_date:
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

        self.run_sync_csv_files(reschedule=True, include_archives=True)

        # perform some tasks a short time after startup
        backup_time_of_day = config.backup_time_of_day
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

    def schedule_database_tasks(self, delay_seconds=0, include_archives=False):
        # run the database tasks once, via the scheduler
        self._scheduler.enter(
            delay=delay_seconds,
            priority=0,
            action=self.run_database_tasks,
            kwargs={"backup_time_of_day": None, "reschedule": False, 
                    "include_archives":include_archives},
        )

    def backup_active_database(self, backup_filename=None):
        try:
            with self._backup_lock:
                self._datastore.backup_active_database(backup_filename)
        except Exception as ex:
            _logger.error(
                f"Error backing up active database: {ex}, {traceback.format_exc()}"
            )
            raise

    def archive_data(self, data_dir):
        try:
            with self._backup_lock:
                _logger.debug(f"Archiving old records from active database")
                self._datastore.archive_data(data_dir=self._config.data_dir)
        except Exception as ex:
            _logger.error(f"Error archiving data from activte database: {ex}")
            raise

    def upload_data(self):
        """
        Copy all data from config.data_dir to an ftp server, with the exception
        of the active database files located in config.data_dir/current

        see sync_folder_to_ftp for details
        """
        with self._backup_lock:
            # Obtain file server information comes from the [ftp] section of
            # config file
            # [ftp]
            # server=ftp.ansto.gov.au
            # directory=
            # username=XXX
            # password=XXX
            data_dir = self._config.data_dir
            c = self._config.ftp
            server = c.server
            user = c.user
            passwd = c.passwd
            directory = c.directory
            if (
                server is not None
                and user is not None
                and passwd is not None
                and directory is not None
            ):
                sync_folder_to_ftp(
                    dirname_local=data_dir,
                    server=server,
                    user=user,
                    passwd=passwd,
                    dirname_remote=directory,
                )

    def sync_legacy_files(self, data_dir, include_archives=False):
        try:
            with self._csv_output_lock:
                _logger.debug("Writing data to legacy file format")
                try:
                    self._datastore.sync_legacy_files(data_dir, include_archives=include_archives)
                except Exception as ex:
                    _logger.error(f"Unable to sync legacy files because of error {ex}.  {traceback.format_exc()}")
        except Exception as ex:
            _logger.error(f"Error syncing legacy csv files: {ex}")

    @task_description("Sync csv files")
    def run_sync_csv_files(self, reschedule=True, include_archives=False):
        """
        Sync the csv files and re-schedule
        """
        # there may be a long delay (e.g. network drives), so allow
        # this routine to hang without bringing down the entire program
        with self._heartbeat_time_lock:
            self._tolerate_hang = True
        self.sync_legacy_files(data_dir=self._config.data_dir, include_archives=include_archives)

        if reschedule:
            # re-schedule next sync at 15 sec after 30 minute interval
            delay_seconds = next_interval(time.time(), interval=30 * 60, offset=15)
            # when rescheduling, don't "include_archives"
            self._scheduler.enter(
                delay=delay_seconds,
                priority=0,
                action=self.run_sync_csv_files,
                kwargs={"reschedule": True},
            )

        self.update_heartbeat_time()
        with self._heartbeat_time_lock:
            self._tolerate_hang = False

    @task_description("Backup active database and sync csv files")
    def run_database_tasks(
        self, backup_time_of_day: datetime.time = None, reschedule=True, include_archives=False,
    ):
        if backup_time_of_day is None:
            # default, one minute past midnight
            backup_time_of_day = datetime.time(0, 1)

        # there may be a long delay (e.g. network drives), so allow
        # this routine to hang without bringing down the entire program
        with self._heartbeat_time_lock:
            self._tolerate_hang = True

        # sleep here allows other database threads (which may be scheduled on the minute)
        # to have a chance to run first
        time.sleep(1)
        t0 = datetime.datetime.now(datetime.timezone.utc)
        # run tasks
        self.sync_legacy_files(data_dir=self._config.data_dir, include_archives=include_archives)
        self.archive_data(data_dir=self._config.data_dir)
        self.backup_active_database()
        t = datetime.datetime.now(datetime.timezone.utc)
        _logger.info(f"Database backup, archive, and legacy file export took {t-t0}")
        self.upload_data()

        if reschedule:
            # re-schedule next backup
            next_backup = datetime.datetime.combine(
                t.date(), backup_time_of_day
            ).replace(tzinfo=datetime.timezone.utc)
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
            self._tolerate_hang = False


def sync_folder_to_ftp(
    dirname_local,
    server,
    user,
    passwd,
    dirname_remote,
    patterns_to_ignore=["current", "current/**", ".ftp-sync-marker"],
):
    """
    Recursively upload files from a local directory to a ftp server

    This is a stopgap until an alternative to ftp backups is found.  There
    are some known limitations:
     - the parent of dirname_remote, the remote directory, needs to exist
     - a file is created in dirname_local, the loal directory, called
       .ftp-sync-marker
       This is the only piece of information used to decide whether or not to
       upload files.  Any file which has a modification time newer than
       .ftp-sync-marker is sent to the ftp server.  The contents of the
       server is not examined at all.
     - probably others exist too

    Arguments
    =========
    *patterns_to_ignore*
     don't upload files which match these patterns
     -- patterns are relative to dirname_local
    """
    if not dirname_remote.startswith("/"):
        dirname_remote = "/" + dirname_remote

    sync_ref = Path(dirname_local, ".ftp-sync-marker")
    if sync_ref.exists():
        t0 = sync_ref.stat().st_mtime
    else:
        t0 = 0

    def matchany(p):
        for pattern in patterns_to_ignore:
            if p.match(pattern):
                return True
        return False

    # find out what needs to be uploaded
    uploads = []
    for p in Path(dirname_local).rglob("*"):
        relp = p.relative_to(dirname_local)
        if p.stat().st_mtime > t0 and not matchany(relp):
            source = p
            dest_dir = Path(dirname_remote).joinpath(relp.parent).as_posix()
            dest_file = relp.parts[-1]
            uploads.append((source, dest_dir, dest_file))
        else:
            _logger.debug(f"Sync to FTP, skipping: {relp}")

    try:
        # use FTP to upload files
        with FTP(server) as ftp:
            ftp.login(user=user, passwd=passwd)

            remote_cwd = "/"
            ftp.cwd(remote_cwd)
            for source, dest_dir, dest_file in uploads:
                # change dir on remote, only if needed, handle
                # creating dir if necessary
                if not dest_dir == remote_cwd:
                    try:
                        ftp.cwd(dest_dir)
                    except ftplib.error_perm:
                        # TODO: handle multiple levels?
                        ftp.mkd(dest_dir)
                        ftp.cwd(dest_dir)
                    remote_cwd = dest_dir
                # upload file or create dir
                if source.is_file():
                    _logger.info(f"Sync to FTP, uploading: {str(source)}")
                    ftp.storbinary(f"STOR {dest_file}", source.open("rb"))
                elif source.is_dir():
                    try:
                        ftp.mkd(dest_file)
                    except ftplib.error_perm:
                        # likely that this folder already exists
                        pass
    except Exception as ex:
        _logger.error(
            f"Failed to sync files to FTP server: {server}, user:{user}, "
            f"remote location: {dirname_remote} because of error: {ex}"
        )
        return

    # on success, update the sync marker
    sync_ref.touch()
