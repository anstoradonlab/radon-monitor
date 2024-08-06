# -*- coding: utf-8 -*-

import copy
import datetime
import os
import tempfile

import pytest
from ansto_radon_monitor.datastore import DataStore, TableStorage

__author__ = "Alan Griffiths"
__copyright__ = "Alan Griffiths"
__license__ = "mit"

t0 = datetime.datetime.now(datetime.timezone.utc).replace(
    microsecond=0, second=0, minute=0, hour=0
)
row = {"Datetime": t0, "RecNum": 103, "LLD": 123.0, "DetectorName": "DetectorA"}

class DataStoreConfigStub:
    udp_destination = None
    pass



def test_datastore(tmp_path):

    config = DataStoreConfigStub()
    config.data_file = str(tmp_path / "data.db")
    print("Testing datastore in", tmp_path)

    ds = DataStore(config)

    assert ds.get_update_time("TEST", "DetectorA") is None
    ds.add_record("TEST", row)
    ds.add_record("TEST", row)
    assert ds._get_table_names_from_disk() == ["detector_names", "persistent_state", "TEST"]
    del ds
    # re-open data store
    ds = DataStore(config)

    assert ds.get_update_time("TEST", "DetectorA") == row["Datetime"]

    assert ds.tables == ["detector_names", "persistent_state", "TEST"]

    t, rows = ds.get_rows("TEST", start_time=None)
    assert row["Datetime"] == rows[0]["Datetime"]
    assert (rows) == ([row, row])

    t, rows = ds.get_rows("TEST", start_time=t0 + datetime.timedelta(hours=1))
    assert rows == []


def test_datastore_with_rollover(tmp_path):
    config = DataStoreConfigStub()
    config.data_file = str(tmp_path / "data-other.db")
    archive_dir = tmp_path

    print("Testing datastore in", tmp_path)
    ds = DataStore(config)


    # mock data
    #   - old so it triggers roll-over
    #   - contains duplicates

    told = t0 - datetime.timedelta(days=62)
    row = {"Datetime": told, "RecNum": 103, "LLD": 123.0, "DetectorName": "DetectorA"}
    data = []
    ## about two months' of 10-sec data
    #num_good = 24*60*6 * 62
    num_good = 1000
    num_duplicates = 50
    dt = datetime.timedelta(seconds=10)
    for ii in range(num_good):
        r = copy.deepcopy(row)
        r['Datetime'] += ii*dt
        data.append(r)
    for ii in range(num_duplicates):
        r = copy.deepcopy(row)
        r['Datetime'] += ii*dt
        data.append(r)


    ds.add_records("TEST", data)
    
    ds.archive_data(str(archive_dir))