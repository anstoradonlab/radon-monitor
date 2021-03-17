import copy
import datetime
import logging
import threading
from collections import defaultdict

_logger = logging.getLogger(__name__)


class DataStore(object):
    def __init__(self):
        self._data_lock = threading.RLock()
        _logger.debug(f"DataStore created.")
        self.__data = defaultdict(list)
        self._last_insertion_time = defaultdict(lambda: datetime.datetime(1900,1,1))

    @property
    def data(self):
        with self._data_lock:
            return copy.deepcopy(self.__data)

    def add_record(self, table, data):
        with self._data_lock:
            _logger.debug(f"Received data for {table}: {data} ")
            self._last_insertion_time[table] = datetime.datetime.utcnow()
            self.__data[table].append(data)
    
    def get_update_time(self, table):
        """Return the time when `table` was updated

        Parameters
        ----------
        table : str
            Name of the data table

        Returns
        -------
        datetime
            Update time according to the timestamp of the most recent time record.  If 
            no timestamp can be found, fall back to returning the time of the last update
            in utc.
        """
        with self._data_lock:
            if not table in self.__data:
                # no data yet for this table, return a time in the past
                most_recent_time = datetime.datetime(1900,1,1)
            else:
                most_recent_row = self.__data[table][-1]
                try:
                    most_recent_time = most_recent_row['Datetime']
                except KeyError:
                    _logger.error(f'No time information found in table: {table}')
                    most_recent_time = self._last_insertion_time[table]
        return most_recent_time
