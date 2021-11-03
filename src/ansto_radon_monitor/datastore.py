#%%
import csv
import datetime
import logging
import pathlib
import sqlite3
import threading
import typing
from collections import defaultdict
from sqlite3.dbapi2 import OperationalError

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
        id = threading.get_ident()
        if not id in self._connection_per_thread:
            _logger.info(f"thread {id} connecting to database {self.data_file}")
            con = sqlite3.connect(
                self.data_file,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            con.row_factory = sqlite3.Row
            self._connection_per_thread[id] = con

            if not self._readonly:
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

        return self._connection_per_thread[id]

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

    def _get_table_names_from_disk(self):
        cur = self.con.cursor()
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        except sqlite3.ProgrammingError as ex:
            # sqlite3.ProgrammingError: Cannot operate on a closed database.
            if ex.args == ("Cannot operate on a closed database.",):
                _logger.warning(f"Attempted to read data from a closed database")
                return []
            else:
                raise ex

        table_names = [itm[0] for itm in cur.fetchall()]
        # filter out the 'detector_names' table
        # TODO: check that this is a sensible thing to do.  Maybe it would make sense to
        # include a "data tables" property instead.  Check how this is being used.
        table_names = [itm for itm in table_names if not itm == "detector_names"]
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
            If there is not any time information in the table, fall back to returning
            the time of the last update in utc.
        """
        t0 = datetime.datetime.utcnow()
        cur = self.con.cursor()
        # note: can't combine 'max' with automatic conversion from timestamp
        # optimisation - run the query only on recent data
        view_name = "Recent" + table_name
        if detector_name is None:
            sql = f"select max(Datetime) from {view_name}"
        else:
            detector_id = self.detector_id_from_name(detector_name)
            sql = f"select max(Datetime) from {view_name} where DetectorName='{detector_id}'"
        most_recent_time = None
        try:
            tstr = tuple(cur.execute(sql).fetchall()[0])[0]
            try:
                most_recent_time = datetime.datetime.strptime(tstr, "%Y-%m-%d %H:%M:%S")
            except Exception as ex:
                _logger.error(
                    f"Error parsing most recent time in database.  sql: {sql}, time string: '{tstr}'"
                )
        except sqlite3.OperationalError as ex:
            _logger.debug(f"SQL exception: {ex} while executing {sql}")

        _logger.debug(
            f"Executing SQL: {sql}, returned: {most_recent_time}, took: {datetime.datetime.utcnow()-t0}"
        )
        return most_recent_time

    def get_rows(self, table_name, start_time, maxrows=1000, recent=True):
        """
        Get data from table beginning with start_time

        TODO: doc fully
        TODO: the 'start_time' should be replaced or augmented with a rowid
        """
        t0 = datetime.datetime.utcnow()

        rowid_max = self.con.execute(f"select max(rowid) from {table_name}").fetchall()[
            0
        ]["max(rowid)"]
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

    def shutdown(self):
        """call this before shutdown"""
        self.con.close()


#%%

if __name__ == "__main__":

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
            "Datetime": datetime.datetime(2021, 10, 23, 12, 30),
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
