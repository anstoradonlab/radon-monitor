import logging
import time
import serial

SERIAL_PORT = "COM5"

logformat = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d %(threadName)s] %(message)s"

# Uncomment to see the low-level details
#logging.basicConfig(level=logging.DEBUG, format=logformat)



#
# ... test using a serial port object instead of a PyLink
#

import serial
from pycampbellcr1000 import CR1000

# create a serial port object, but don't open it
ser = serial.Serial(port=None, 
                    baudrate=115200,
                    timeout=2,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=1)
ser.port = SERIAL_PORT
cr1000 = CR1000(ser)

#cr1000 = CR1000.from_url(f"serial:{SERIAL_PORT}:115200", timeout=2)

print(cr1000)
print(cr1000.pakbus.link)

print(cr1000.settings)

for ii in range(10):
    tick = time.time()
    # Obtain the table definitions
    tdfdata = cr1000.getfile(".TDF")
    tock = time.time()
    print(f".TDF data length: {len(tdfdata)}, acquired in {tock-tick} sec")

#for row in cr1000.get_data_generator("Results"):
#    print(len(row))

