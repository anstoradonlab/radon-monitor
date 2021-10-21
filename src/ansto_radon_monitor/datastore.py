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


class TableStorage:
    def __init__(self, base_dir, table_name):
        self.max_elements = 2000
        self._data_lock = threading.RLock()
        self.base_dir = pathlib.Path(base_dir).resolve()
        self.name = table_name
        self.latest_time = None
        self._data = self.load_from_disk()
        self._last_insertion_time = datetime.datetime.utcnow()

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

    def _trim_data(self, data):
        """Keep no more than a certain number of records in memory"""
        if len(data) > self.max_elements:
            # TODO: move this down to Table
            n = len(self._data) - self.max_elements
            data_trimmed = data[n:]
        else:
            data_trimmed = data
        return data_trimmed

    def _init_file(self, p, headers):
        with self._data_lock:
            if not p.exists():
                pp = p.parent
                pp.mkdir(parents=True, exist_ok=True)
                with open(p, "wt") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(headers)
                _logger.debug(f"Created {p}")

    def readfile(self, p, start_time=None):
        data = []

        # Type conversions to perform when reading
        # note: default is -
        #   * first column is a timestamp
        #   * for other columns, first try converting to float, the try bool,
        #  but leave as string if that fails
        def conv_from_csv(v):
            try:
                v = float(v)
            except ValueError:
                v = {"True": True, "False": False}[v]
            return v

        typeconv = {"RecNbr": int}

        with open(p, "rt") as csvfile:
            reader = csv.reader(csvfile)
            headers = reader.__next__()
            rownum = 1
            for row in reader:
                if not len(row) == len(headers):
                    _logger.error(
                        f"Error reading {p}, line number {rownum}.  Expected {len(headers)} fields but got {len(row)}"
                    )
                # first column is always timestamp
                fmt = "%Y-%m-%d %H:%M:%S"
                row[0] = datetime.datetime.strptime(row[0], fmt)
                # update the 'latest_time' field
                if self.latest_time is None or row[0] > self.latest_time:
                    self.latest_time = row[0]
                row_as_dict = {k: v for k, v in zip(headers, row)}
                # convert types
                for k in row_as_dict:
                    # don't touch the first column
                    if not k == headers[0]:
                        convertor_func = typeconv.get(k, conv_from_csv)
                        try:
                            row_as_dict[k] = convertor_func(row_as_dict[k])
                        except:
                            # convertor failed - leave the data alone
                            pass
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
                self._data = self._trim_data(self._data)
                # also store to disk
                self._init_file(p, headers)
                with open(p, "at") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(row)

            self._last_insertion_time = datetime.datetime.utcnow()

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

            data = self._trim_data(data)

        return data

    def get_update_time(self):
        """Return the time when the table was updated, according to the timestamp in the time record
           If the table has not yet been created, return None
        """
        return self.latest_time

    def get_rows(self, start_time):
        with self._data_lock:
            ret = [
                itm
                for itm in self._data
                if start_time is None or itm["Datetime"] > start_time
            ]
        return ret


def rowtime(row):
    """return the timestamp for a row. Row may be in a few different forms.
    """
    if "Datetime" in row:
        # dict case
        return row["Datetime"]
    # list case
    return row[0]


class DataStore(object):
    def __init__(self, base_dir):
        self.base_dir = pathlib.Path(base_dir)
        self._tables = {}
        self._data_lock = threading.RLock()
        self._init_from_disk()

    def add_record(self, table_name, data):
        with self._data_lock:
            if not table_name in self._tables:
                self._tables[table_name] = TableStorage(self.base_dir, table_name)

            self._tables[table_name].store_row(data)

    def _get_table_names_from_disk(self):
        p = self.base_dir
        fnames = p.glob("????/??/??-*.csv")
        tables = set()
        for itm in fnames:
            table = str(itm.name)[3:].split(".csv")[0]
            tables.add(table)
        return sorted(list(tables))

    def _init_from_disk(self):
        with self._data_lock:
            tables = self._get_table_names_from_disk()
            _logger.debug(f"Found tables on disk: {tables}")
            for k in tables:
                self._tables[k] = TableStorage(self.base_dir, k)

    @property
    def data(self):
        data_ret = {}
        with self._data_lock:
            for t in self._tables.values():
                data_ret[t.name] = t.data
        return data_ret

    @property
    def tables(self):
        "a list of table names"
        return list(self._tables.keys())

    def get_update_time(self, table_name):

        """Return the time when `table` was updated

        Parameters
        ----------
        table_name : str
            Name of the data table

        Returns
        -------
        datetime
            Update time according to the timestamp of the most recent time record.
            If the table has not yet been created, return None
            If there is not any time information in the table, fall back to returning 
            the time of the last update in utc.
        """
        with self._data_lock:
            if not table_name in self._tables:
                # no data yet for this table, return a time in the past
                _logger.debug(f'Table "{table_name}" does not yet exist in datastore.')
                most_recent_time = None
            else:
                most_recent_time = self._tables[table_name].get_update_time()
        return most_recent_time

    def get_rows(self, table, start_time):
        with self._data_lock:
            t = self.get_update_time(table)
            return t, self._tables[table].get_rows(start_time)

    def shutdown(self):
        """currently there's nothing to do"""
        pass


if __name__ == "__main__":
    fn = "/home/alan/working/2021-03-radon-monitor-software/ansto_radon_monitor/data/2021/03/18-cal.csv"
