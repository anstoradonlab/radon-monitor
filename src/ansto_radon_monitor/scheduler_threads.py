import copy
import datetime
import functools
import logging
import math
import sched
import sys
import threading
import time

from pycampbellcr1000 import CR1000

_logger = logging.getLogger()

from .labjack_interface import CalBoxLabjack


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
    return (math.ceil(sec / interval) * interval) - sec


class DataThread(threading.Thread):
    """
    Base thread for data-oriented threads.  Sits in a loop and runs tasks,
    and can be shutdown cleanly from another thread.
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

    def shutdown(self):
        self.cancelled = True
        self.state_changed.set()

    @property
    def done(self):
        return _done

    def measurement_func(self):
        _logger.debug(f"Taking measurement at {datetime.datetime.now()}")
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
            except AttributeError:
                desc = str(task.action)
            return f"{t} {desc}"

        with self._lock:
            ret = [task_to_readable(itm) for itm in self._scheduler.queue]
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
        _logger.debug("entered run")
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

        _logger.debug("finished run - calling shutdown_func")
        self.shutdown_func()


class CalibrationUnitThread(DataThread):
    def __init__(self, labjack_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "CalibrationUnitThread"
        self._labjack = CalBoxLabjack(labjack_id)
        self._data_table_name = "calibration-unit"
        # task priority is used to identify tasks later, so that
        # pending cal and background can be cancelled by the user
        self._calibration_tasks_priority = 10
        self._background_tasks_priority = 15

    @task_description("Calibration unit: flush source")
    def set_flush_state(self):
        self._labjack.flush()

    @task_description("Calibration unit: inject from source")
    def set_inject_state(self):
        self._labjack.inject()

    @task_description("Calibration unit: switch to background state")
    def set_background_state(self):
        self._labjack.start_background()

    @task_description("Calibration unit: return to idle")
    def set_default_state(self):
        self._labjack.reset_all()

    @task_description("Calibration unit: cancel background")
    def cancel_background(self):
        # self._labjack.reset_background()
        self._labjack.reset_all()
        # TODO: handle case when source is still flushing

    def measurement_func(self):
        t = datetime.datetime.utcnow()
        t = t.replace(microsecond=0)
        data = {"Datetime": t}
        data.update(copy.deepcopy(self._labjack.digital_output_state))
        data.update(self._labjack.analogue_states)
        data["status"] = self.status
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
                priority=100,
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

        _logger.debug(
            f"run_calibration, parameters are flush_duration:{flush_duration}, inject_duration:{inject_duration}, start_time:{start_time}"
        )

        p = self._calibration_tasks_priority
        if start_time is not None:
            initial_delay_seconds = max(
                0, (start_time - datetime.datetime.utcnow()).total_seconds()
            )
        else:
            initial_delay_seconds = 0
        #
        # begin flushing
        self._scheduler.enter(
            delay=initial_delay_seconds, priority=p, action=self.set_flush_state,
        )
        # start calibration *on* the half hour
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
        # reset the background flags
        self._scheduler.enter(
            delay=delay_inject_start, priority=p, action=self.cancel_background,
        )
        # and start injection (at the same time)
        self._scheduler.enter(
            delay=delay_inject_start, priority=p, action=self.set_inject_state,
        )

        # stop injection
        delay_inject_stop = delay_inject_start + inject_duration
        self._scheduler.enter(
            delay=delay_inject_stop, priority=p, action=self.set_default_state,
        )

        self.state_changed.set()

    def run_background(self, duration, start_time=None):
        """Run the calibration sequence - flush source, inject source

        Parameters
        ----------
        duration : float
            duration of background period (sec)
        start_time : datetime.datetie or None, optional
            time when flushing is due to start (UTC), or None (which means to start
            immediately), by default None
        """

        p = self._background_tasks_priority
        if start_time is not None:
            initial_delay_seconds = max(
                0, (start_time - datetime.datetime.utcnow()).total_seconds()
            )
        else:
            initial_delay_seconds = 0
        #
        # begin background
        self._scheduler.enter(
            delay=initial_delay_seconds, priority=p, action=self.set_background_state,
        )
        # reset the background flags
        self._scheduler.enter(
            delay=initial_delay_seconds + duration,
            priority=p,
            action=self.cancel_background,
        )

        self.state_changed.set()

    @task_description("Calibration unit: measure state")
    def cancel_calibration(self):
        """cancel an in-progress calibration and all pending ones"""
        tasks_to_remove = [
            itm
            for itm in self._scheduler.queue
            if itm.priority == self._calibration_tasks_priority
        ]
        for itm in tasks_to_remove:
            self._scheduler.cancel(itm)

        # schedule a task to reset the cal box
        self._scheduler.enter(
            delay=0, priority=0, action=self.set_default_state,
        )

        self.state_changed.set()

    @property
    def status(self):
        return self._labjack.status


def fix_record(record):
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
    return r


class DataLoggerThread(DataThread):
    def __init__(self, datalogger_config, *args, **kwargs):
        # TODO: include type annotations
        super().__init__(*args, **kwargs)
        self.measurement_interval: int = 5  # TODO: from config?, this is in seconds
        self._config: Configuration = datalogger_config
        self._datalogger: CR1000 = CR1000.from_url(
            datalogger_config.serial_port, timeout=2
        )
        # TODO: handle 'unable to connect' error
        if hasattr(self._datalogger.pakbus.link, "baudrate"):
            _logger.info(
                f"Connected to datalogger using serial port, baudrate: {self._datalogger.pakbus.link.baudrate}"
            )
        self.tables = [str(itm, "ascii") for itm in self._datalogger.list_tables()]
        # Filter the tables - only include the ones which are useful
        tables_to_use = ["Results", "RTV"]
        self.tables = [itm for itm in self.tables if itm in tables_to_use]
        self.name = "DataLoggerThread"
        self.status = "Connected"

    def measurement_func(self):
        # TODO: handle lost connection
        self.status = "Retrieving data from datalogger"
        with self._lock:
            for table_name in self.tables:
                destination_table_name = self._config.name + "-" + table_name
                update_time = self._datastore.get_update_time(destination_table_name)
                if update_time is not None:
                    update_time += datetime.timedelta(seconds=1)

                for data in self._datalogger.get_data_generator(
                    table_name, start_date=update_time
                ):
                    # return early if another task is trying to execute
                    # (likely this is a shutdown request)
                    if self.state_changed.is_set():
                        return
                    if len(data) > 0:
                        _logger.debug(
                            f"Received data ({len(data)} records) from table {destination_table_name} with start_date = {update_time}."
                        )

                        for itm in data:
                            self._datastore.add_record(
                                destination_table_name, fix_record(itm)
                            )
