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
        run_measurement_on_startup=True,
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

        return [task_to_readable(itm) for itm in self._scheduler.queue]

    @property
    def seconds_until_next_measurement(self):
        now = time.time()
        delay = next_interval(now, self.measurement_interval, self.measurement_offset)
        return delay

    @task_description("Run a measurement")
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
    def __init__(self, labjack, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "CalibrationUnitThread"
        self._labjack = labjack
        self.status = 'Normal operation'


    @task_description("Calibration unit: flush source")
    def set_flush_state(self):
        self.digital_output_state["activate_pump"] = True
        self.digital_output_state["activate_inject"] = False

        self._send_state_to_device()

    @task_description("Calibration unit: inject from source")
    def set_inject_state(self):
        self._labjack.inject()

    @task_description("Calibration unit: return to idle")
    def set_default_state(self):
        self._labjack.reset()

    def measurement_func(self):
        # check the state matches the class's state
        # set the state on the instrument matches (log an error if not)
        # measure stats
        # send measurement to datastore
        
        t = datetime.datetime.utcnow()
        t = t.replace(microsecond=0)
        data = copy.deepcopy(self._labjack.digital_output_state)
        data['ch0','ch1'] = self._labjack.analogue_states
        data['Datetime'] = t

        self._datastore.add_record(data)

    @task_description("Calibration unit: measure state")
    def run_measurement(self):
        """call measurement function and schedule next"""
        self.measurement_func()
        self._scheduler.enter(
            delay=self.seconds_until_next_measurement,
            priority=0,
            action=self.run_measurement,
        )

    def run_calibration(self, flush_duration, inject_duration, start_time=None):

        calibration_tasks_priority = 10

        # begin flushing immediately
        self._scheduler.enter(
            delay=0,
            priority=calibration_tasks_priority,
            action=self.set_flush_state,
        )
        # start calibration *on* the half hour
        sec_per_30min = 30*60
        now = time.time()
        delay_inject_start = next_interval(now + flush_duration, sec_per_30min) + flush_duration
        self._scheduler.enter(
            delay=delay_inject_start,
            priority=calibration_tasks_priority,
            action=self.set_inject_state,
        )
        # stop injection
        delay_inject_stop = delay_inject_start + inject_duration
        self._scheduler.enter(
            delay=delay_inject_stop,
            priority=calibration_tasks_priority,
            action=self.set_default_state,
        )

        self.state_changed.set()


    def cancel_calibration(self):
        calibration_tasks_priority = 10
        tasks_to_remove = [itm for itm in self._scheduler.queue if itm.priority == calibration_tasks_priority]
        for itm in tasks_to_remove:
            self._scheduler.cancel(itm)
        
        self.state_changed.set()

    def get_calibration_status(self):
        pass



class DataLoggerThread(threading.Thread):
    def __init__(self, datalogger_port, *args, **kwargs):
        kwargs["name"] = "DataLoggerThread"
        self.measurement_interval = 5  # TODO: from config?, this is in seconds
        self._datalogger = CR1000.from_url(datalogger_port, timeout=10)
        self.tables = [str(itm, 'ascii') for itm in self._datalogger.get_tables()]
        super().__init__(*args, **kwargs)

    def measurement_func(self):
        
        for k in self.tables:
            update_time = self._datastore