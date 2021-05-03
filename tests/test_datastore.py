# -*- coding: utf-8 -*-

import pytest
import tempfile
import os
import datetime
import copy

from ansto_radon_monitor.datastore import DataStore, TableStorage

__author__ = "Alan Griffiths"
__copyright__ = "Alan Griffiths"
__license__ = "mit"

t0 = datetime.datetime.utcnow().replace(microsecond=0, second=0, minute=0, hour=0)
row = {"Datetime": t0, "RecNum": 103, "LLD": 123.0}


def test_large_table():
    # test that we can roll over large tables
    with tempfile.TemporaryDirectory() as tmpdirname:
        t = TableStorage(tmpdirname, "TEST")
        for ii in range(t.max_elements + 10):
            rowc = {}
            rowc.update(row)
            rowc["Datetime"] += datetime.timedelta(seconds=ii)
            t.store_row(rowc)
        assert len(t.data) == t.max_elements


def test_tablestorage():
    # temp_dir = tempfile.TemporaryDirectory()
    # tmpdirname = temp_dir.name
    # temp_dir.cleanup()

    # if True:
    with tempfile.TemporaryDirectory() as tmpdirname:
        print("Testing datastore in", tmpdirname)
        # test creating datastore in empty (but existing) directory
        t = TableStorage(tmpdirname, "TEST")
        assert t.headers == []
        t.store_row(row)

        # test that repeated write does nothing
        assert len(t.data) == 1
        t.store_row(row)
        assert len(t.data) == 1

        fn_store = t._file_for_record(row["Datetime"])
        print(fn_store)
        assert os.path.exists(fn_store)
        with open(fn_store, "rt") as fd:
            fd.readline()
            stored_row = fd.readline()

            fd.seek(0)
            print(fd.read())

        data_saved = copy.deepcopy(t.data)

        del t

        # check re-load from disk
        t = TableStorage(tmpdirname, "TEST")
        assert t.data == data_saved
        assert t.data[-1] == row
        assert t.headers == list(row.keys())

        # check 'last time' functionality
        assert t.get_update_time() == row["Datetime"]


def test_datastore():

    with tempfile.TemporaryDirectory() as tmpdirname:
        print("Testing datastore in", tmpdirname)
        # test creating datastore in empty (but existing) directory
        ds = DataStore(tmpdirname)

    with tempfile.TemporaryDirectory() as tmpdirname:
        print("Testing datastore in", tmpdirname)
        store_dir = os.path.join(tmpdirname)
        ds = DataStore(tmpdirname)
        assert ds.get_update_time("TEST") is None
        ds.add_record("TEST", row)
        assert ds._get_table_names_from_disk() == ["TEST"]
        del ds
        # re-open data store
        ds = DataStore(tmpdirname)

        assert ds.data["TEST"][-1] == row
        assert ds.get_update_time("TEST") == row["Datetime"]

        assert ds.tables == ["TEST"]

        t, rows = ds.get_rows("TEST", start_time=None)
        assert rows == [row]

        t, rows = ds.get_rows("TEST", start_time=t0 + datetime.timedelta(hours=1))
        assert rows == []

    with pytest.raises(AssertionError):
        assert False
