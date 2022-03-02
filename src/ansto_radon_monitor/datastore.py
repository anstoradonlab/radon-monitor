#%%
import csv
import datetime
import logging
import os
import pathlib
import sqlite3
import sys
import threading
import time
import traceback
import typing
from collections import defaultdict
from sqlite3.dbapi2 import OperationalError

_logger = logging.getLogger(__name__)


# database time format
DBTFMT = "%Y-%m-%d %H:%M:%S"

# utility functions
def next_year_month(y, m):
    m += 1
    if m > 12:
        m = 1
        y += 1
    return y, m


def iter_months(tmin, tmax):
    """
    >>> import datetime
    >>> tmin = datetime.datetime(2005, 6, 12)
    >>> tmax = datetime.datetime(2006, 2, 8)
    >>> list(iter_months(tmin,tmax))
    [(2005, 6),
    (2005, 7),
    (2005, 8),
    (2005, 9),
    (2005, 10),
    (2005, 11),
    (2005, 12),
    (2006, 1),
    (2006, 2)]
    """
    y = tmin.year
    m = tmin.month
    while y < tmax.year or m <= tmax.month:
        yield y, m
        y, m = next_year_month(y, m)


# TODO: reorganise + clean up


def log_backtrace_all_threads():
    for th in threading.enumerate():
        _logger.error(f"Thread {th}")
        # print(f"Thread {th}", file=sys.stderr)
        msg = "".join(traceback.format_stack(sys._current_frames()[th.ident]))
        _logger.error(f"{msg}")
        # print(f"{msg}", file=sys.stderr)


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
    """return the timestamp for a row. Row may be in a few different forms."""
    if "Datetime" in row:
        # dict case
        return row["Datetime"]
    # list case
    return row[0]


class CSVDataStore(object):
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


def column_definition(column_name):
    """
    return column definition (in sql format) which can be joined together
    using ',' and then used as a CREATE TABLE argument
    """

    # Special columns - foreign key support
    if column_name in ["DetectorName"]:
        return (
            "DetectorName integer, "
            "FOREIGN KEY(DetectorName) REFERENCES detector_names(id)"
        )

    dtype = ""
    # standard data columns - return a definition like: "column_name data_type"
    # e.g. "Datetime timestamp"
    # strip _Avg, _Tot suffix from column names
    if column_name.endswith("_Avg") or column_name.endswith("_Tot"):
        k = column_name[:-4]
    else:
        k = column_name

    known_cols = {
        "Datetime": "timestamp",
        "status": "text",
        "comment": "text",
        "RecNbr": "integer",
        "ExFlow": "float",
        "InFlow": "float",
        "Gas_meter": "float",
        "RelHum": "float",
        "TankP": "float",
        "Pres": "float",
        "HV": "float",
        "PanTemp": "float",
        "BatV": "float",
        "LLD": "integer",
        "ULD": "integer",
    }

    if k in known_cols:
        dtype = known_cols[k]

    # handle multiple LLD/ULD columns (e.g. LLD1, LLD2, ...)
    elif column_name.startswith("LLD") or column_name.startswith("ULD"):
        dtype = "integer"
    else:
        dtype = ""

    return f"{column_name} dtype".strip()


class DataStore(object):
    """
    Data store backed by a sqlite database
    """

    def __init__(self, config, readonly=False):
        self.data_file = str(config.data_file)
        self._config = config
        self._connection_per_thread = {}
        self._data_lock = threading.RLock()
        self._readonly = readonly

        # the last row_id returned by "get_rows" per table
        self._last_rowid = {}

        # this forces an immediate connection to the database
        # so that any errors will occur now (rather than once
        # data has been acquired)
        con = self.con

    @property
    def con(self) -> sqlite3.Connection:
        """
        Database connection

        Enables options for type conversion and sqlite3's Row object
        """
        # default timeout is 5 seconds - make this much longer
        # (in testing, no DB operations take more than about 4 seconds)
        timeout_seconds = 60 * 5
        # timeout_seconds = 1 # for testing (finds failure points)
        tid = threading.get_ident()
        if not tid in self._connection_per_thread:
            _logger.info(f"thread {tid} connecting to database {self.data_file}")
            # ensure directory exists
            db_directory = os.path.dirname(self.data_file)
            if not os.path.exists(db_directory):
                os.makedirs(db_directory)
            con = sqlite3.connect(
                self.data_file,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                timeout=timeout_seconds,
            )
            con.row_factory = sqlite3.Row
            self._connection_per_thread[tid] = con

            if not self._readonly:
                # improve write speed an concurrency (at the expense of extra files on disk)
                # https://www.sqlite.org/wal.html
                con.execute("PRAGMA journal_mode=WAL")
                con.execute("PRAGMA synchronous=NORMAL")
                # enable foreign key support
                con.execute("PRAGMA foreign_keys = 1")
                # check that this worked
                for r in con.execute("PRAGMA foreign_keys"):
                    Ok = r["foreign_keys"] == 1
                    if not Ok:
                        _logger.warning(
                            "Foreign key support is not enabled in SQLite database"
                        )
                # create a table to store the detector names (as a space saving optimisation)
                con.execute(
                    "CREATE TABLE IF NOT EXISTS detector_names (id INTEGER PRIMARY KEY, name TEXT UNIQUE)"
                )

        return self._connection_per_thread[tid]

    def create_table(self, table_name, data):
        cur = self.con.cursor()
        keys = list(data.keys())
        # dtypes = [database_dtype(itm) for itm in keys]
        # definitions = [" ".join([k, dtype]).strip() for k, dtype in zip(keys, dtypes)]
        # sql = f"CREATE TABLE {table_name} ({ ','.join(definitions) })"
        table_definition = ",".join((column_definition(itm) for itm in keys))
        # -- use the 'if not exists' in case another thread beats us here
        sql = f"CREATE TABLE if not exists {table_name} ({table_definition})"
        _logger.debug(f"Executing SQL: {sql}")
        cur.execute(sql)
        # create a view of this table which shows only the latest data
        # (makes 'get_update_time' execute more quickly)
        view_name = "Recent" + table_name
        if table_name == "Results":
            # 10 days?
            nrows = 1440 * 6 * 2  # twice the batchsize in mock data generator
        else:
            nrows = 1440 * 6 * 2  # twice the batchsize in mock data generator
        sql = f"CREATE VIEW if not exists {view_name} as SELECT * from {table_name} ORDER BY rowid DESC LIMIT {nrows}"
        cur.execute(sql)
        self.con.commit()

    def get_column_names(self, table_name):
        db_column_names = [
            itm["name"] for itm in self.con.execute(f"PRAGMA table_info({table_name})")
        ]
        return db_column_names

    def modify_table(self, table_name, data):
        # work out which columns are not present in the table at present
        column_names = list(data.keys())
        db_column_names = [
            itm["name"] for itm in self.con.execute(f"PRAGMA table_info({table_name})")
        ]
        missing_column_names = [
            itm for itm in column_names if not itm in db_column_names
        ]
        # print('-----------\n'+ '\n'.join((dict(itm).__repr__() for itm in db_column_names))+'\n----------')
        # add each missing column to the table
        for column_name in missing_column_names:
            _logger.warning(
                f'Adding missing column ({column_name}) to table "{table_name}"'
            )
            col_definition = column_definition(column_name)
            sql = f"ALTER TABLE {table_name} ADD {col_definition}"
            self.con.execute(sql)
        self.con.commit()

    def add_record(self, table_name, data):
        self.add_records(table_name, [data])

    def add_records(self, table_name, data):

        if len(data) == 0:
            _logger.warning(
                "Programming error (?) - add_records called with zero-length data"
            )
            return

        cur = self.con.cursor()
        column_names = list(data[0].keys())
        sql = f"insert into {table_name} ({','.join(column_names)}) values ({ ','.join(['?']*len(data[0])) })"
        _logger.debug(f"Executing SQL: {sql}")

        # special handling for DetectorName
        # this replaces a detector name with an ID
        if "DetectorName" in data[0].keys():
            names = set((itm["DetectorName"] for itm in data))
            for n in names:
                # TODO: this could be done just once at startup
                # (insert or ignore info from )
                cur.execute(
                    "insert or ignore into detector_names values (Null, ?)", (n,)
                )
            self.con.commit()

            cur = self.con.cursor()
            rows = cur.execute("select * from detector_names")
            name_to_id = {}
            for r in rows:
                name_to_id[r["name"]] = r["id"]

            for itm in data:
                itm["DetectorName"] = name_to_id[itm["DetectorName"]]

        row0 = data[0]
        data_without_headers = [tuple(itm.values()) for itm in data]

        # _logger.debug(f"About to insert data: {data_without_headers}")

        try:
            # if len(data_without_headers) == 1:
            #    cur.execute(sql, data_without_headers[0])
            # else:
            cur.executemany(sql, data_without_headers)
        except sqlite3.OperationalError as ex:
            # table doesn't exist yet
            _logger.debug(f"SQL error: {ex}")
            if ex.args[0].startswith("no such table:"):
                self.create_table(table_name, row0)
            # an error message like: "table calibration_unit has no column named comment"
            elif (
                ex.args[0]
                .lower()
                .startswith(f"table {table_name.lower()} has no column named")
            ):
                # new column(s) have somehow appeared in the table
                self.modify_table(table_name, row0)
            else:
                raise ex

            # if len(data_without_headers) == 1:
            #    cur.execute(sql, data_without_headers[0])
            # else:
            cur.executemany(sql, data_without_headers)
        self.con.commit()

    def _get_table_names_from_disk(self, has_datetime=None):
        try:
            cur = self.con.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        except sqlite3.ProgrammingError as ex:
            # sqlite3.ProgrammingError: Cannot operate on a closed database.
            if ex.args == ("Cannot operate on a closed database.",):
                _logger.warning(f"Attempted to read data from a closed database")
                return []
            else:
                raise ex

        table_names = [itm[0] for itm in cur.fetchall()]
        if has_datetime is None:
            pass
        elif has_datetime:
            table_names = [
                itm for itm in table_names if "Datetime" in self.get_column_names(itm)
            ]
        else:
            table_names = [
                itm
                for itm in table_names
                if not "Datetime" in self.get_column_names(itm)
            ]
        ## filter out the 'detector_names' table
        ## TODO: check that this is a sensible thing to do.  Maybe it would make sense to
        ## include a "data tables" property instead.  Check how this is being used.
        ##table_names = [itm for itm in table_names if not itm == "detector_names"]
        return table_names

    @property
    def data(self):
        return NotImplementedError()
        data_ret = {}
        with self._data_lock:
            for t in self.tables.values():
                data_ret[t.name] = t.data
        return data_ret

    @property
    def tables(self):
        "a list of table names"
        return self._get_table_names_from_disk()

    @property
    def data_tables(self):
        "a list of tables containing a 'Datetime' column (containing time data)"
        return self._get_table_names_from_disk(has_datetime=True)

    @property
    def static_tables(self):
        "a list of tables without a 'Datetime' column (static in time)"
        return self._get_table_names_from_disk(has_datetime=False)

    def detector_id_from_name(self, detector_name):
        """Lookup the detector's ID from its name"""
        cur = self.con.cursor()
        rows = cur.execute(
            'select * from detector_names where "name"=?', (detector_name,)
        )
        for r in rows:
            return r["id"]

    def get_update_time(self, table_name, detector_name):

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

            TODO: (maybe) If there is not any time information in the table, fall back to returning
            the time of the last update in utc.
        """
        t0 = datetime.datetime.utcnow()
        cur = self.con.cursor()
        # note: can't combine 'max' with automatic conversion from timestamp
        # optimisation - run the query only on recent data
        # view_name = "Recent" + table_name
        view_name = table_name
        if detector_name is None:
            sql = f"select max(Datetime) from {view_name}"
        else:
            detector_id = self.detector_id_from_name(detector_name)
            sql = f"select max(Datetime) from {view_name} where DetectorName='{detector_id}'"
        most_recent_time = None
        try:
            tstr = tuple(cur.execute(sql).fetchall()[0])[0]
            # tstr will be None if there are no rows in the database yet
            try:
                most_recent_time = datetime.datetime.strptime(tstr, "%Y-%m-%d %H:%M:%S")
            except Exception as ex:
                _logger.error(
                    f"Error parsing most recent time in database.  sql: {sql}, time string: '{tstr}'"
                )
                log_backtrace_all_threads()
        except sqlite3.OperationalError as ex:
            _logger.debug(f"SQL exception: {ex} while executing {sql}")

        _logger.debug(
            f"Executing SQL: {sql}, returned: {most_recent_time}, took: {datetime.datetime.utcnow()-t0}"
        )
        return most_recent_time

    def get_minimum_time(self, table_name):
        """
        Return the earliest time in the table

         - slow (scan across all records)
        """
        if table_name is None:
            min_times = []
            for table_name in self.tables:
                if "Datetime" in self.get_column_names(table_name):
                    min_times.append(self.get_minimum_time(table_name))
            # TODO:decide what to do if there are no Datetime columns, depending on how this function is used
            # currently min([]) --> raises ValueError
            return min(min_times)

        t0 = datetime.datetime.utcnow()
        sql = f"select min(Datetime) from {table_name}"
        try:
            tstr = tuple(self.con.execute(sql).fetchall()[0])[0]
            try:
                min_time = datetime.datetime.strptime(tstr, "%Y-%m-%d %H:%M:%S")
            except Exception as ex:
                _logger.error(
                    f"Error parsing most recent time in database.  sql: {sql}, time string: '{tstr}'"
                )
                raise ex
        except sqlite3.OperationalError as ex:
            _logger.debug(f"SQL exception: {ex} while executing {sql}")
            raise ex

        _logger.debug(
            f"Executing SQL: {sql}, returned: {min_time}, took: {datetime.datetime.utcnow()-t0}"
        )
        return min_time

    def get_rows(self, table_name, start_time, maxrows=1000, recent=True):
        """
        Get data from table beginning with start_time

        TODO: doc fully
        TODO: the 'start_time' should be replaced or augmented with a rowid
        """
        t0 = datetime.datetime.utcnow()

        # protect against "closed database" happening at any point in this code block
        try:
            # load detector names into a dict
            detector_names_dict = {}
            try:
                rows = self.con.execute("select * from detector_names")
                for r in rows:
                    detector_names_dict[r["id"]] = r["name"]
            except Exception as e:
                _logger.error(f'Unable to read "detector_names" table, error: {e}')

            rowid_max = self.con.execute(
                f"select max(rowid) from {table_name}"
            ).fetchall()[0]["max(rowid)"]
            last_rowid = self._last_rowid.get(table_name, 0)
            self._last_rowid[table_name] = rowid_max

            # create a temporary view which only contains the data seen since the last
            using_a_view = False
            if recent:
                view_name = "recent_" + table_name
                self.con.execute(f"drop view  if exists {view_name}")
                self.con.execute(
                    f"create temp view {view_name} as select * from {table_name} where rowid > {last_rowid}"
                )
                using_a_view = True
            else:
                view_name = table_name

            # Execute SQL along the lines of:
            # SELECT * FROM tablename
            # WHERE columname >='2012-12-25 00:00:00'
            # AND columname <'2012-12-26 00:00:00'
            # Note: this uses a subset (e.g. see https://stackoverflow.com/questions/7786570/get-another-order-after-limit)
            if start_time is not None:
                t_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
                sql = f"SELECT * from (SELECT * FROM {view_name} WHERE Datetime > '{t_str}' ORDER BY Datetime DESC LIMIT {maxrows}) as T1 order by Datetime ASC"
            else:
                sql = f"SELECT * from (SELECT * FROM {view_name} ORDER BY Datetime DESC LIMIT {maxrows}) as T1 ORDER BY Datetime ASC"
            _logger.debug(f"Executing SQL: {sql}")
            try:
                cursor = self.con.execute(sql)
            except sqlite3.OperationalError as ex:
                # sqlite3.OperationalError: no such column: Datetime
                if ex.args == ("no such column: Datetime",):
                    _logger.warning(f"Datetime column not found in table {view_name}")
                    return None, []
                else:
                    raise ex
        except sqlite3.ProgrammingError as ex:
            # sqlite3.ProgrammingError: Cannot operate on a closed database.
            if ex.args == ("Cannot operate on a closed database.",):
                _logger.warning(f"Attempted to read data from a closed database")
                return None, []
            else:
                raise ex

        # convert sqlite3.Row objects into plain python dicts
        data = [dict(itm) for itm in cursor]
        # convert detector ids to their full names
        def lookup_name(row):
            if "DetectorName" in row.keys():
                detector_id = row["DetectorName"]
                detector_name = detector_names_dict.get(detector_id, detector_id)
                row["DetectorName"] = detector_name
            return row

        data = [lookup_name(itm) for itm in data]

        if len(data) == 0:
            # no data obtained, so t is unchanged
            t = start_time
            # t = self.get_update_time(table_name, detector_name=None)
        else:
            t = max((itm["Datetime"] for itm in data))
            # if t is a string, convert to python datetime at this point
            if not hasattr(t, "strptime"):
                t = datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S")

                def conv_date(itm):
                    itm["Datetime"] = datetime.datetime.strptime(
                        itm["Datetime"], "%Y-%m-%d %H:%M:%S"
                    )
                    return itm

                data = [conv_date(itm) for itm in data]

        _logger.debug(
            f"Loading data (rows: {len(data)}, table: {view_name}, start time: {start_time}, max_t: {t}) took: {datetime.datetime.utcnow()-t0}"
        )

        return t, data

    def get_archive_filename(self, data_dir, y, m):
        fname = os.path.abspath(
            os.path.join(data_dir, "archive", f"{y}-{m:02}-radon.db")
        )
        return fname

    def get_archive_db(self, data_dir, y, m, con):
        """
        Return a filename, and a database connection where either:
         - the database exists and has the same structure as the active database
         - the database did not exist, but it has been created (empty) with the structure copied from the active database
        """
        # create database if needed
        archive_dir = os.path.join(data_dir, "archive")
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
        fname_archive_root = os.path.abspath(
            os.path.join(data_dir, "archive", f"{y}-{m:02}-radon.db")
        )
        fname_archive = fname_archive_root
        filename_counter = 0
        existing_structure = self.get_structure_sql(con)

        while True:
            if not os.path.exists(fname_archive):
                archive_exists = False
                con_archive = sqlite3.connect(fname_archive)
                break
            con_archive = sqlite3.connect(fname_archive)
            db_structure_matches = "".join(existing_structure) == "".join(
                self.get_structure_sql(con_archive)
            )
            if db_structure_matches:
                archive_exists = True
                break
            _logger.debug(f"Unable to use {fname_archive} as archive database")
            filename_counter += 1
            fname_archive = fname_archive_root + "." + str(filename_counter)
            _logger.debug(f"Trying {fname_archive} as archive database")
            if filename_counter > 60:
                raise RuntimeError()

        if not archive_exists:
            # copy structure from source to destination db
            _logger.debug(
                f"Copying database structure into new database {fname_archive}"
            )
            with con_archive:
                for (sql,) in con.execute(
                    "select sql from sqlite_master where sql is not NULL"
                ):
                    _logger.debug(f"Executing sql: {sql}")
                    con_archive.execute(sql)

        # copy some tables in their entirety (these are assumed to be short)
        # this is done even if the database already exists, in case of changes
        with con_archive:
            for table_name in self.static_tables:
                con_archive.execute(f"DELETE FROM {table_name}")
                _logger.debug(f"Copying table {table_name}")
                for row in con.execute(f"select * from {table_name}"):
                    con_archive.execute(
                        f"insert into {table_name} values ({','.join('?'*len(row))})",
                        row,
                    )
                _logger.debug(f"Finished copying table {table_name}")

        return fname_archive, con_archive

    def get_structure_sql(self, con):
        return [
            itm[0]
            for itm in con.execute(
                "select sql from sqlite_master where sql is not NULL"
            ).fetchall()
        ]

    def archive_data(self, data_dir):
        """
        Move old data into archives
        """
        # open a plain connection to the live database (no type conversions etc)
        con = sqlite3.connect(
            self.data_file,
        )

        maximum_age = datetime.timedelta(days=35)
        threshold_time = datetime.datetime.now() - maximum_age
        # are there any records older than "threshold_time"?
        database_mintime = self.get_minimum_time(None)
        if not database_mintime < threshold_time:
            _logger.debug(
                f"No data old enough to archive (oldest data is from {database_mintime} but needs to be from earlier than {threshold_time}"
            )
            return
        # iterate over all tables containing a DateTime column
        for table_name in self.data_tables:
            db_column_names = [
                itm[1] for itm in con.execute(f"PRAGMA table_info({table_name})")
            ]
            db_column_names_sql = ",".join(db_column_names)
            cursor = con.cursor()
            for y, m in iter_months(database_mintime, threshold_time):
                t0_query = datetime.datetime(y, m, 1, 0, 0, 0)
                y1, m1 = next_year_month(y, m)
                t1_query = datetime.datetime(y1, m1, 1, 0, 0, 0)

                fname_archive, con_archive = self.get_archive_db(data_dir, y, m, con)
                t0 = datetime.datetime.utcnow()
                with con:
                    cur = con.cursor()
                    # 10 days of data at 1 sample/10 second
                    # (controls the number of rwos returned by fecthmany)
                    cur.arraysize = 14400 * 0
                    with con_archive:
                        # the steps here are (timing for 10-sec table)
                        #  1. query (to find the rows to move, happens lazily and very quickly)
                        #  2. copy rows (takes about 4.4 seconds)
                        #  3. delete rows in activate database (takes about 1.1 seconds)
                        a = time.time()
                        rows = cur.execute(
                            f'select {db_column_names_sql} from {table_name} WHERE Datetime >= "{t0_query.strftime(DBTFMT)}" and Datetime < "{t1_query.strftime(DBTFMT)}"'
                        )
                        print("TIMING1:", time.time() - a)
                        a = time.time()
                        count = 0
                        sql = f"insert into {table_name} values ({','.join('?'*len(db_column_names))})"

                        if False:
                            # this is the simple, but slightly slower, version
                            for count, row in enumerate(rows):
                                con_archive.execute(sql, tuple(row))
                            nrows = count + 1
                        elif True:
                            cur_archive = con_archive.cursor()
                            cur_archive.executemany(sql, (tuple(itm) for itm in rows))
                            nrows = cur_archive.rowcount
                        else:
                            # this is the faster, but slightly more complex, version
                            while True:
                                chunk = rows.fetchmany()
                                print(len(chunk))
                                if len(chunk) == 0:
                                    break
                                count += len(chunk)
                                con_archive.executemany(sql, chunk)
                            nrows = count
                        print("TIMING2", time.time() - a)
                        a = time.time()
                        cur.execute(
                            f'delete from {table_name} WHERE Datetime >= "{t0_query.strftime(DBTFMT)}" and Datetime < "{t1_query.strftime(DBTFMT)}"'
                        )
                        print("TIMING3", time.time() - a)
                        ### - note I intended to do this in chunks, but the first approach I took wasn't working (no order by compiled into my sqlite delete clause)
                        ### - just start by copying everything, and then change things if that is too slow.
                        # # old code - intended to copy in chunks
                        # rows = cur.execute(f'select * from {table_name} WHERE Datetime >= \"{t0_query.strftime(DBTFMT)}\" and Datetime < \"{t1_query.strftime(DBTFMT)}\" order by rowid limit 1000')

                        # for count, row in enumerate(rows):
                        #     # TODO: executemany with executemany(...).rowcount
                        #     sql = f"insert into {table_name} values ({','.join('?'*len(row))})"
                        #     con_archive.execute(sql, tuple(row))
                        # nrows = count + 1
                        # cur.execute(f'delete from {table_name} WHERE Datetime >= \"{t0_query.strftime(DBTFMT)}\" and Datetime < \"{t1_query.strftime(DBTFMT)}\" order by rowid limit 1000')
                        # if nrows < 1000: # this means we're done
                        #     break
                _logger.info(
                    f"Archiving data for {y}-{m:02} from table {table_name} ({nrows} rows) took {datetime.datetime.utcnow() - t0}"
                )
                # sleep to give other tasks a chance to access the database
                time.sleep(0.25)

    def backup_active_database(self, backup_fn=None):
        """
        Backup the active database
        """
        if not hasattr(self.con, "backup"):
            _logger.warning(
                "Backing up the live database requires Python version >= 3.7"
            )
        return

        if backup_fn is None:
            data_dir = self._config.data_dir
            archive_dir = os.path.join(data_dir, "archive")
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
            backup_fn = os.path.join(archive_dir, "radon-backup.db")

        def progress(status, remaining, total):
            _logger.debug(
                f"Database backup copied {total-remaining} of {total} pages..."
            )

        _logger.debug(f"Backing up datastore to {backup_fn}")
        con = self.con
        bck = sqlite3.connect(backup_fn)
        with bck:
            # copy in 10 Mb chunks, sleep for .25 seconds
            # in between each call to copy
            con.backup(bck, pages=1024 * 10, progress=progress, sleep=0.25)
        bck.close()

    def sync_legacy_files(self, data_dir):
        """
        Write csv file in the old file format

         - assume that locking is taken care by the caller
         - the file name pattern is defined by configuration options
        """

        if data_dir is None:
            data_dir = self._config.data_dir

        table_name = "Results"

        tz_offset = datetime.timedelta(
            seconds=int(self._config.legacy_file_timezone * 3600)
        )
        tmin_local = self.get_minimum_time(table_name) - tz_offset
        tmax_local = self.get_update_time(table_name, None) - tz_offset

        # define month names statically to prevent any interction with user's
        # local settings (from list(calendar.month_abbr) )
        month_abbr = [
            "",
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]

        # columns to retrieve
        cols_to_skip = {"RecNbr", "DetectorName", "id", "name"}
        colnames = [
            itm for itm in self.get_column_names(table_name) if not itm in cols_to_skip
        ]

        def format_rec(row, headers=False):
            """format a row, if headers is True then format for headers

            The format is intended to match this:
                Year, DOY, Month, DOM, Time,  ExFlow, GM, InFlow, HV, Spare,LLD, ULD, TankP, Temp, AirT, RelHum, Press,  Batt, Comments, Flag
                2020, 306,11,01,00:00, 45.42, 681, 8.12, 578.9, 2126, 1400, 0, 18.17, 34.56, 23.87, 63.83, 1009.168, 13.73,, 0

            """
            output = []
            if headers:
                for itm in row.keys():
                    if itm == "Datetime":
                        # special case - this gets expanded
                        output.extend(("Year", "DOY", "Month", "DOM", "Time"))
                    else:
                        # strip the "_Tot" etc. suffix
                        if itm.endswith("_Tot") or itm.endswith("_Avg"):
                            itm = itm[:-4]
                        output.append(itm)
                output_str = ", ".join(output)
                # two spaces after 'Time' in the headers
                output_str.replace("Time, ", "Time,  ")
            else:
                for k, itm in zip(row.keys(), row):
                    assert itm == row[k]
                    if k == "Datetime":
                        itm = datetime.datetime.strptime(itm, DBTFMT)
                        doy = itm.timetuple().tm_yday
                        itm_str = f"{itm.year}, {doy},{itm.month},{itm.day}, {itm.strftime('%H:%M')}"
                        output.append(itm_str)
                    elif itm is not None:
                        output.append(str(itm))
                    else:
                        output.append("")
                output_str = ", ".join(output)
                # match the quirk of the comment column
                output_str = output_str.replace(", ,", ",,")
            return output_str

        # iterate over each month from t0 to t1
        for y, m in iter_months(tmin_local, tmax_local):
            # work out t
            # two digit year
            yy = y % 100
            m_txt = month_abbr[m]
            t0_query = datetime.datetime(y, m, 1, 0, 0, 0) - tz_offset
            y1, m1 = next_year_month(y, m)
            t1_query = datetime.datetime(y1, m1, 1, 0, 0, 0) - tz_offset

            # TODO:
            # get detector names from database?
            # what if config has changed?
            for detector_config in self._config.detectors:
                detector_name = detector_config.name
                exec_t0 = datetime.datetime.utcnow()
                sql = (
                    f"SELECT {','.join(colnames)} from Results LEFT OUTER JOIN detector_names ON Results.DetectorName=detector_names.id "
                    f'WHERE Datetime >= "{t0_query.strftime(DBTFMT)}" and Datetime < "{t1_query.strftime(DBTFMT)}" and name = "{detector_name}"'
                )

                try:
                    data = self.con.execute(sql).fetchall()
                except Exception as ex:
                    _logger.error(f"Error ({ex}) while executing sql: {sql}")
                    raise ex
                _logger.debug(
                    f"Executing sql: {sql} took {datetime.datetime.utcnow() - exec_t0}"
                )
                numrows = len(data)
                if numrows == 0:
                    # skip this file - no data
                    continue
                fname = (
                    detector_config.csv_file_pattern.replace("{MONTH}", m_txt)
                    .replace("{YEAR}", f"{yy:02}")
                    .replace("{NAME}", detector_name)
                )
                fname = os.path.abspath(os.path.join(self._config.data_dir, fname))
                # check - does the output file already exist and contain at least as many rows
                #         as there are in the database query
                #         (this is all that is checked, e.g. if the table definition has changed there
                #          will be a mess made FIXME )
                csv_needs_update = True
                if os.path.exists(fname):
                    file_size_mb = os.path.getsize(fname) / 1024 / 1024
                    # if the file size is larger than 10 Mbytes, it is very
                    # unlikely that we want to overwrite it and loading a large
                    # file to count the lines might be slow or otherwise unwise
                    # The files we expect to see are more like 200 kBytes in size
                    if file_size_mb > 100:
                        _logger.error(
                            f"Skipping output to {fname} because there is already a file on disk which is over 100 Mbytes in size ({file_size_mb} Mbytes)"
                        )
                        # bail out here to avoid loading the file
                        continue

                    with open(fname, "rt") as fd:
                        for count, _ in enumerate(fd):
                            pass
                        numrows_in_file = count + 1

                    if numrows_in_file >= numrows + 1:
                        # file has one extra row, for headers
                        csv_needs_update = False

                if csv_needs_update:
                    _logger.info(f"Updating csv file {fname}")
                    # create a directory if necessary
                    dirname = os.path.abspath(os.path.dirname(fname))
                    if not os.path.exists(dirname):
                        _logger.info(f"Creating directory {dirname}")
                        os.makedirs(dirname)

                    with open(fname, "wt") as fd:
                        fd.write(format_rec(data[0], headers=True))
                        fd.write("\n")
                        for row in data:
                            fd.write(format_rec(row))
                            fd.write("\n")

    def shutdown(self):
        """call this before shutdown"""
        self.con.close()


#%%

if __name__ == "__main__":
    import sys

    def setup_logging(loglevel=logging.DEBUG):
        """Setup basic logging

        Args:
            loglevel (int): minimum loglevel for emitting messages
        """
        # logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
        logformat = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d %(threadName)s] %(message)s"
        logging.basicConfig(
            level=loglevel,
            stream=sys.stdout,
            format=logformat,
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # exclude messages for Pylink and Pycr1000
        class Blacklist(logging.Filter):
            def __init__(self):
                self.blacklist = ["pycampbellcr1000", "pylink"]

            def filter(self, record):
                """return True to keep message"""
                return not record.name in self.blacklist

        for handler in logging.root.handlers:
            handler.addFilter(Blacklist())

    setup_logging()

    class TestConfig:
        data_file = "test.sqlite"

    config = TestConfig()
    ds = DataStore(config)
    con = ds.con
    for result in con.execute("PRAGMA foreign_keys"):
        print(result)
    con.execute("PRAGMA foreign_keys = 1")
    # check that this worked
    for r in con.execute("PRAGMA foreign_keys"):
        Ok = r["foreign_keys"] == 1
        assert Ok

    data = [
        {
            "Datetime": datetime.datetime(2021, 9, 23, 12, 30),
            "RecNbr": 382393,
            "ExFlow_Tot": 0.0,
            "InFlow_Avg": -13.84,
            "LLD_Tot": 0.0,
            "ULD_Tot": 0.0,
            "Gas_meter_Tot": 0.0,
            "AirT_Avg": -168.9,
            "RelHum_Avg": 34.86,
            "TankP_Avg": -558.7,
            "Pres_Avg": 419.6658020019531,
            "HV_Avg": -712.7,
            "PanTemp_Avg": 21.26,
            "BatV_Avg": 15.24,
            "DetectorName": "TEST_002M",
        }
    ]
    ds.add_records("Results", data)

    print(ds.get_update_time("Results", "TEST_002M"))

    print(ds.get_update_time("ThisTableDoesNotExist", "TEST_002M"))

    #%%
    for row in ds.con.execute("""Select * from Results"""):
        print(dict(row))

    for row in ds.con.execute("""Select * from detector_names"""):
        print(dict(row))

    #%%
    for row in ds.con.execute(
        """Select * from Results 
                                 left join detector_names on Results.DetectorName=detector_names.id
                                 limit 10"""
    ):
        print(dict(row))

    #%%
    ds.archive_data(".\data-archive-test")

    #%%
    ds.backup_activate_database(".\data-archive-test")

    #%%
    if False:
        fn = "/home/alan/working/2021-03-radon-monitor-software/ansto_radon_monitor/data/2021/03/18-cal.csv"
        print("hello")

        import datetime
        import sqlite3

        con = sqlite3.connect(
            "test.sqlite", detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )

        sql = "drop table Results"
        con.execute(sql)

        sql = "CREATE TABLE Results (Datetime timestamp,RecNbr,Flag i2)"
        try:
            con.execute(sql)
        except sqlite3.OperationalError as ex:
            print(ex)

        sql = "INSERT into Results(Datetime,RecNbr,Flag)  values (?,?,?)"
        con.execute(sql, (datetime.datetime.now(), 1, False))
        con.commit()

        sql = "SELECT * from Results"

        [
            (
                datetime.datetime(2021, 10, 24, 7, 30),
                382431,
                0.0,
                -13.84,
                0.0,
                0.0,
                0.0,
                -168.9,
                34.86,
                -558.7,
                419.6658020019531,
                -712.7,
                21.26,
                15.24,
                "TEST_002M",
            )
        ]

        cur = con.execute(sql)
        for itm in cur.fetchall():
            print(itm)

        # con.close()

# %%
