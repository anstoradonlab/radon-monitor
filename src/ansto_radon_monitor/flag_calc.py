"""
Calculate the "flag" column from information in the database
"""

import datetime
import typing
import sqlite3

from .data_util import parse_date


def floor_t(t: datetime.datetime):
    """
    Floor t to the nearest 30 minutes
    """
    if t.minute > 30:
        return t.replace(minute=30, second=0, microsecond=0)
    else:
        return t.replace(minute=0, second=0, microsecond=0)

def ceil_t(t: datetime.datetime):
    tfloor = floor_t(t)
    # this handles the case where t is already
    # exactly on the half-hour
    if t - tfloor > datetime.timedelta(seconds=0):
        tceil = tfloor + datetime.timedelta(minutes=30)
    else:
        tceil = tfloor
    
    return tceil

def load_times_list(con_list, sql, is_t0_func, is_t1_func,  
                    t0_offset=datetime.timedelta(seconds=0), 
                    t1_offset=datetime.timedelta(seconds=0)):
    """_summary_

    This works on a list of database connections because of the possibility
    that an event might cross the boundary between calendar months.

    Args:
        con_list (_type_): _description_
        sql (_type_): _description_
        is_t0_func (bool): _description_
        is_t1_func (bool): _description_

    Returns:
        list of (t0,t1,detector): 
            t0 rounded down to a multiple of 30 minutes,
            t1 is rounded up to a multiple of 30 minutes
            detector is the name of the detector which this
            time interval applies to, or None if it applies
            to all detectors.
    """
    data = []
    for con in con_list:
        try:
            data.extend(con.execute(sql).fetchall())
        except sqlite3.OperationalError:
            # possible for the sqlite query to fail, e.g. 
            # sqlite3.OperationalError: no such column: Detector
            pass
    data.sort(key=lambda x: x['Datetime'])

    # find t0,t1 pairs
    t0 = None
    times_list = []
    for itm in data:
        if is_t0_func(itm) and t0 is None:
            t0 = floor_t(parse_date(itm["Datetime"])) + t0_offset
            detector = itm["Detector"]
        if is_t1_func(itm) and t0 is not None:
            t1 = ceil_t(parse_date(itm["Datetime"])) + t1_offset
            times_list.append( (t0, t1, detector) )
            t0 = None
            detector = None
    if t0 is not None:
        t1 = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(days=1000)
        times_list.append( (t0, t1, detector) )
 
    return times_list


def load_cals(con_list):
    sql = """SELECT
                Datetime,EventData,Detector
             FROM 
                LogMessages
             WHERE
                EventType == "CalibrationEvent" OR EventType == "SystemEvent"
             ORDER BY
                Datetime
            """
    def is_t0_func(itm):
        return itm["EventData"].startswith("Began injecting radon from calibration source into detector")
    def is_t1_func(itm):
        return itm["EventData"] == "Left calibration state" or itm["EventData"] == "Shutdown"
    
    t1_offset = datetime.timedelta(hours=6)
    
    times_list = load_times_list(con_list, sql, is_t0_func, is_t1_func, t1_offset=t1_offset)

    return times_list


def load_maintenence_mode(con_list: typing.List[sqlite3.Connection]) -> typing.List[typing.Tuple[datetime.datetime, datetime.datetime]]:
    sql = """SELECT
                Datetime,EventData,Detector
             FROM 
                LogMessages
             WHERE
                EventType == "MaintenanceMode"
             ORDER BY
                Datetime
            """
    def is_t0_func(itm):
        return itm["EventData"] == 1
    def is_t1_func(itm):
        return itm["EventData"] == 0

    times_list = load_times_list(con_list, sql, is_t0_func, is_t1_func)
    return times_list

def load_backgrounds(con_list: typing.List[sqlite3.Connection]) -> typing.List[typing.Tuple[datetime.datetime, datetime.datetime]]:
    sql = """SELECT
                Datetime,EventData,Detector
             FROM 
                LogMessages
             WHERE
                EventType == "CalibrationEvent" OR EventType == "SystemEvent"
             ORDER BY
                Datetime
            """
    def is_t0_func(itm):
        return itm["EventData"].startswith("Began background cycle on detector")
    def is_t1_func(itm):
        return itm["EventData"] == "Left background state" or itm["EventData"] == "Shutdown"
    
    times_list = load_times_list(con_list, sql, is_t0_func, is_t1_func)
    return times_list


class FlagCalculator(object):

    FLAG_OK = 0
    FLAG_BG = 1
    FLAG_CAL = 2
    FLAG_MM = 3
    FLAG_OTHER = 7

    def __init__(self, con_list: typing.List[sqlite3.Connection]):
        self._con_list = con_list
        self._load_metadata()

    def _load_metadata(self):
        # lists of start/stop times
        self._bg = load_backgrounds(self._con_list)
        self._cal = load_cals(self._con_list)
        self._mm = load_maintenence_mode(self._con_list)
        # TODO: this is not implemented yet
        self._bad = []
        for con in self._con_list:
            # do the thing
            pass
    
    def _is_in_interval(self, interval_list, t, detector: str):
        # linear search, not expecting a very many intervals
        for t0,t1,d in interval_list:
            if d is None or detector is None or d == detector:
                if t > t0 and t <= t1:
                    return True
        return False           

    def flag(self, t: datetime.datetime, detector: str) -> int:
        """Calculate flag value at time t

        Args:
            t datetime.datetime: 
            Time, UTC, when to calculate flag.  t is taken to
            be the time at the end of a sampling interval

            detector str:
            Name of the detector, as a string, to calculate the flag for
        """
        if self._is_in_interval(self._bg, t, detector):
            return self.FLAG_BG
        if self._is_in_interval(self._cal, t, detector):
            return self.FLAG_CAL
        if self._is_in_interval(self._mm, t, detector):
            return self.FLAG_MM
        if self._is_in_interval(self._bad, t, detector):
            return self.FLAG_OTHER
        return self.FLAG_OK

