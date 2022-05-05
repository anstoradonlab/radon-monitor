import datetime
import logging
import os
import pprint
import time

from pycampbellcr1000 import CR1000

# logging.basicConfig(level=logging.DEBUG)


if os.name == "nt":
    cr1000 = CR1000.from_url("serial:COM8:115200")  # timeout=2
else:
    cr1000 = CR1000.from_url("serial://dev/ttyUSB0:115200")

print(f"Link information: {cr1000.pakbus.link._serial}")

logger_info = cr1000.getprogstat()

print(logger_info)

file_info = cr1000.list_files()


pprint.pprint(file_info)

fname = str(logger_info["ProgName"], "utf-8")

print(fname)
print("=" * len(fname))
print()

print(str(cr1000.getfile(fname), "utf8"))

time.sleep(1)
print("getting .TDF file, ten times")
for ii in range(10):
    tick = time.time()
    tdfdata = cr1000.getfile(".TDF")
    tock = time.time()
    print(f"tdf data length: {len(tdfdata)}, acquired in {tock-tick} sec")

print("Testing get_data_generator")


t0 = datetime.datetime(1970, 1, 1)

for table_name in ["Results"]:
    for data in cr1000.get_data_generator(table_name, start_date=t0):
        if len(data) > 0:
            print(
                f"Received data from {table_name}, length: {len(data)}, first row: {data[0]}"
            )
