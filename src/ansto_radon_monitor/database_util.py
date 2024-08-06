import logging
import sqlite3
import time
from collections import defaultdict
from logging.handlers import RotatingFileHandler
from sqlite3.dbapi2 import OperationalError
from typing import Union, Dict, Any


_logger = logging.getLogger(__name__)





def deduplicate_table(con: sqlite3.Connection, table_name: str="Results") -> int:
    """Removes duplicate rows from database table.
    
    This modifies the database in-place.  It works by:
        - copying all distinct records into a new (temporary) table
        - deleting the contents of the original table
        - copy the contents back from the temporary table
        - delete the temporary table
    
    This all happens inside a single database transaction, so if any of the steps fail
    then the transaction should be rolled back and the database left unchanged.


    Arguments 
    ---------
    *con* - sqlite3.Connection 
        Database connection object, e.g. from sqlite3.connect(...) 
        
    *table_name* - str, default 'Results' 
        Name of the database table to process. Expected options are: 
            'Results': 30-min data 
            'RTV': 10-sec data 'CalibrationUnit': 10-sec data from the calibration unit 
            'LogMessages': log messages, e.g. start and end time of calibrations 

    Returns 
    ------- 
    number of duplicate records removed
    
    """ 
    
    with con:
        sql = f'select count(*) from "{table_name}"'
        total_records = con.execute(sql).fetchall()[0][0]
        sql = f'select count(*) from (select distinct * from "{table_name}")'
        unique_records = con.execute(sql).fetchall()[0][0]
        if total_records == unique_records:
            return 0
        else:
            num_duplicates = total_records - unique_records
            
            # De-duplicate by 
            # - copying all distinct records into a new (temporary) table
            # - deleting the contents of the original table
            # - copy the contents back from the temporary table
            # - delete the temporary table
            temp_table_name = table_name + "TemporaryCopy7385"
            sql = (f'CREATE TABLE "{temp_table_name}" AS SELECT DISTINCT * FROM "{table_name}";\n'
                   f'DELETE FROM "{table_name}";\n'
                   f'INSERT INTO "{table_name}" SELECT * FROM "{temp_table_name}";\n'
                   f'DROP TABLE "{temp_table_name}";\n' 
                   )
            
            print("***", sql)

            t0 = time.time()
            for itm in sql.split(";\n"):
                con.execute(itm)

            t1 = time.time()
            _logger.info(f"De-duplicating {num_duplicates} records in database table \"{table_name}\" took {t1-t0} seconds.")
    
    with con:
        sql = "VACUUM"
        con.execute(sql)
    
    return num_duplicates

