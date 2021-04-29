import copy
import csv
import datetime
import logging
import pathlib
import threading
import typing
from collections import defaultdict

_logger = logging.getLogger(__name__)


# TODO: reorganise + clean up



class TableStorage():
    def __init__(self, base_directory, table_name):
        self._data_lock = threading.RLock()
        self.base_dir = pathlib.Path(base_directory).resolve()
        self.name = table_name
        self.latest_time = None
        self._data = self.load_from_disk()
        
    def _file_for_record(self, t: datetime.datetime) -> pathlib.Path:
        """file which a particular record should be written to"""
        p = self.base_dir
        fn = t.strftime(f"%Y/%m/%d-{self.name}.csv")
        return pathlib.Path(p, fn)
    
    @property
    def headers(self):
        if len(self._data) == 0:
            return []
        
        return list(self._data[0].keys())
    
    @property
    def data(self):
        return self._data

    def _init_file(self, p, headers):
        with self._data_lock:
            if not p.exists():
                pp = p.parent
                pp.mkdir(parents=True, exist_ok=True)
                with open(p, "wt") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(headers)
                _logger.debug(f'Created {p}')

    def readfile(self, p, start_time=None):
        data = []
        with open(p, 'rt') as csvfile:
            reader = csv.reader(csvfile)
            headers = reader.__next__()
            rownum = 1
            for row in reader:
                if not len(row) == len(headers):
                    _logger.error(f'Error reading {p}, line number {rownum}.  Expected {len(headers)} fields but got {len(row)}')
                # first column is always timestamp
                fmt = '%Y-%m-%d %H:%M:%S'
                row[0] = datetime.datetime.strptime(row[0], fmt)
                # update the 'latest_time' field
                if self.latest_time is None or row[0] > self.latest_time:
                    self.latest_time = row[0]
                row_as_dict = { k:v for k,v in zip(headers, row)}
                # filter rows older than `start_time`
                if start_time is None or row[0] >= start_time:
                    data.append(row_as_dict)
                # this is the row number *in the file*
                rownum += 1
                    
        return headers, data

    def store_row(self, data: typing.Dict):
        
        with self._data_lock:
            # store the latest data on disk
            p = self._file_for_record(data["Datetime"])
            headers = list(data)
            row = list(data.values())
            # only write this row to disk if it is more recent than the 'latest time'
            # TODO: this could result in data loss - maybe we need more checks?
            if self.latest_time is None or row[0] > self.latest_time:
                self.latest_time = row[0]
                # store the latest data in memory
                self._data.append(data)
                # also store to disk
                self._init_file(p, headers)
                with open(p, "at") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(row)
    
    def load_from_disk(self, start_date=None):
        now = datetime.datetime.utcnow()
        if start_date is None:
            start_date = now - datetime.timedelta(days=10)
        t = start_date
        paths = []
        while t < now + datetime.timedelta(days=1):
            paths.append(self._file_for_record(t))
            t += datetime.timedelta(days=1)
        paths = sorted(set(paths))
        paths = filter(lambda p: p.exists(), paths)
        headers = None
        data = []
        for p in paths:
            new_headers, new_data = self.readfile(p, start_date)
            if headers is None:
                headers = new_headers
            if headers == new_headers:
                data.extend(new_data)
            else:
                data = new_data

        return data



def rowtime(row):
    """return the timestamp for a row. Row may be in a few different forms.
    """
    if 'Datetime' in row:
        # dict case
        return row['Datetime']
    #list case
    return row[0]
    


class MultiTableStorage():
    def __init__(self, base_directory):
        self._data_lock = threading.RLock()
        self.base_dir = pathlib.Path(base_directory).resolve()
        self._tables = {}
        self._init_files()
        
    
    @property
    def tables(self):
        """a dictionary mapping table names to table store"""
        return self._tables

    def get_rows(self, table:str, start_time:datetime.datetime=None):
        """load existing data from a table, beginning from `start_date`"""
        with self._data_lock:
            data = self._tables[table].data
            if start_time is not None:
                data = [itm for itm in data if rowtime(itm) > start_time]
            
        return data

    def _init_files(self):
        """initialise files on disk"""
        with self._data_lock:
            p = self.base_dir
            # the third term (any ...) checks that p is not empty
            if p.exists() and p.is_dir() and any(p.iterdir()):
                self._init_from_disk()
            else:
                p.mkdir()

    def _init_from_disk(self):
        names = self._get_table_names_from_disk()
        for name in names:
            self._tables[name] = TableStorage(self.base_dir, name)
            self._tables[name].readfile(self._get_latest_file(name))
            _logger.debug(f'Table {name} initialised.  Latest data is dated {self._tables[name].latest_time}.')

    def _get_latest_subdir(self):
        p = self.base_dir
        y = sorted( p.glob('????'))[-1]
        p = pathlib.Path(p, y)
        m = sorted( p.glob('??'))[-1]
        return pathlib.Path(p, m)
    
    def _get_latest_file(self, table_name):
        p = self._get_latest_subdir()
        return list(p.glob(f'??-{table_name}.csv'))[-1]

    def _get_table_names_from_disk(self):
        p = self._get_latest_subdir()
        tables = set()
        for itm in p.glob('??-*.csv'):
            table = str(itm.name).split('-')[1].split('.csv')[0]
            tables.add(table)
        return sorted(list(tables))

    def _file_for_record(self, table: str, t: datetime.datetime) -> pathlib.Path:
        """file which a particular record should be written to"""
        p = self.base_dir
        fn = t.strftime(f"%Y/%m/%d-{table}.csv")
        return pathlib.Path(p, fn)

    def _init_file(self, p, headers):
        with self._data_lock:
            if not p.exists():
                pp = p.parent
                pp.mkdir(parents=True, exist_ok=True)
                with open(p, "wt") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(headers)
                _logger.debug(f'Created {p}')

    def store_row(self, table: str, data: typing.Dict):
        with self._data_lock:
            try:
                tstore = self.tables[table]
            except KeyError:
                # create the table if it doesn't exist
                self.tables[table] = TableStorage(self.base_dir, table)
                tstore = self.tables[table]
            self.tables[table].store_row(data)

        # with self._data_lock:
        #     p = self._file_for_record(table, data["Datetime"])
        #     headers = list(data)
        #     row = list(data.values())
        #     self._init_file(p, headers)
        #     with open(p, "at") as csvfile:
        #         writer = csv.writer(csvfile)
        #         writer.writerow(row)


class DataStore(object):
    def __init__(self, base_directory):
        # maximum number of elements to keep in memory
        self.max_elements = 2000
        self._data_lock = threading.RLock()
        self.__data = defaultdict(list)
        self._t_init = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        self._last_insertion_time = defaultdict(
            lambda: self._t_init + datetime.timedelta(seconds=1)
        )
        _logger.debug(f"DataStore initializing in {base_directory}.")
        self.tstore = MultiTableStorage(base_directory)
        self._tables = set([])
        for table_name, table in self.tstore.tables.items():
            for itm in table.load_from_disk():
                self.add_record(table_name, itm)
        
        _logger.debug(f"DataStore created.  Tables: {[itm for itm in self.tstore.tables]}")


    @property
    def data(self):
        with self._data_lock:
            return copy.deepcopy(self.__data)

    @property
    def tables(self):
        return sorted(list(self._tables))
    
    def add_record(self, table, data):
        with self._data_lock:
            self._tables.add(table)
            t = datetime.datetime.utcnow()
            # prevent flood of messages
            if t - self._last_insertion_time[table] > datetime.timedelta(seconds=5):
                _logger.debug(f"Received data for {table}: {data} ")
            self._last_insertion_time[table] = t
            self.__data[table].append(data)
            if len(self.__data[table]) > self.max_elements:
                # TODO: move this down to Table
                n = len(self.__data[table]) - self.max_elements
                self.__data[table] = self.__data[table][n:]

            self.tstore.store_row(table, data)

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
                most_recent_time = self._t_init
            else:
                most_recent_row = self.__data[table][-1]
                try:
                    most_recent_time = list(most_recent_row.values())[0]
                except KeyError:
                    _logger.error(f"No time information found in table: {table}")
                    most_recent_time = self._last_insertion_time[table]
        return most_recent_time
    
    def get_rows(self, table, start_time):
        with self._data_lock:
            t = self.get_update_time(table)
            return t, self.tstore.get_rows(table, start_time)

    def shutdown(self):
        """currently there's nothing to do"""
        pass




if __name__ == "__main__":
    fn = '/home/alan/working/2021-03-radon-monitor-software/ansto_radon_monitor/data/2021/03/18-cal.csv'
