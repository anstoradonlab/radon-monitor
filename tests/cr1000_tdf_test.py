import logging
import time

SERIAL_PORT = "COM5"
DO_THE_PATCH = False

logformat = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d %(threadName)s] %(message)s"

# Uncomment to see the low-level details
#logging.basicConfig(level=logging.DEBUG, format=logformat)

#
# Monkey patching
#


# PATCH ##
# - return data from SerialLink as bytes (without conversion to str) and
# - without any adjustments to the timeout
#
# - on my test machine (windows 10 build 1803, FTDI USB-Serial Driver 2.12.36.3 with 
# the default settings) adjusting the timeout in this function seems to be the cause
# of problems, including: lost data and a 10x slowdown in data transfer.
# - these problems are not observed when using the same FTDI dongle running from a Linux
# box or (strangely) when running from WSL.
#
# Since the timeout argument is never used from PyCampbellCR1000, let's just simplify
# this function.

# Here is what we are replacing:
    # def read(self, size=None, timeout=None):
    #     '''Read data from the serial connection. The maximum amount of data
    #     to be received at once is specified by `size`. If `is_byte` is True,
    #     the data will be convert to byte array.'''
    #     size = size or self.MAX_STRING_SIZE
    #     timeout = (timeout or 1) * (self.timeout or 1)
    #     self.serial.timeout = timeout
    #     data = self.serial.read(size)
    #     try:
    #         data = str(data, encoding='utf8')
    #     except:
    #         pass
    #     if len(data) != 0 :
    #         self.log("Read", data)
    #     self.serial.timeout = self.timeout
    #     return data

def read_bytes_but_do_not_mess_with_timeout(self, size=None):
    '''Read data from the serial connection. The maximum amount of data
    to be received at once is specified by `size`.'''
    size = size or self.MAX_STRING_SIZE
    data = self.serial.read(size)
    return data

if DO_THE_PATCH:
    # Monkey-patch the PyLink library
    import pylink
    pylink.link.SerialLink.read = read_bytes_but_do_not_mess_with_timeout


#
# ... test
#

from pycampbellcr1000 import CR1000

cr1000 = CR1000.from_url(f"serial:{SERIAL_PORT}:115200", timeout=1)

for ii in range(10):
    tick = time.time()
    # Obtain the table definitions
    tdfdata = cr1000.getfile(".TDF")
    tock = time.time()
    print(f".TDF data length: {len(tdfdata)}, acquired in {tock-tick} sec")

