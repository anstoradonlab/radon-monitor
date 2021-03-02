import copy
import logging
import threading
from collections import defaultdict

_logger = logging.getLogger(__name__)


class DataStore(object):
    def __init__(self):
        self._data_lock = threading.RLock()
        _logger.debug(f"DataStore created.")
        self.__data = defaultdict(list)

    @property
    def data(self):
        with self._data_lock:
            return copy.deepcopy(self.__data)

    def add_record(self, destination, data):
        with self._data_lock:
            _logger.debug(f"Received data for {destination}: {data} ")
            self.__data[destination].append(data)
