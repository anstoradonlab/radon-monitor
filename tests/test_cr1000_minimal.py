import datetime
import logging
import os
import pprint
import time
import serial

logformat = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d %(threadName)s] %(message)s"

#logging.basicConfig(level=logging.DEBUG, format=logformat)
#logging.basicConfig(level=logging.CRITICAL, format=logformat)

import pylink
import pycampbellcr1000


#
# Monkey patching
#

# PATCH #1
# - do not log every single data transfer during serial port read/write

def log_stub(self, message, data):
    pass

pylink.link.Link.log = log_stub

# PATCH #2
# - do not perform any conversions between bytes and str (in other words, assume that 
# bytes object is passed to write)

# Here is what we are replacing:
# def write(self, data):
#     '''Write all `data` to the serial connection.'''
#     data = format_string(data)
#     self.serial.write(data)
#     try:
#         self.log("Write", str(data, encoding='utf8'))
#     except:
#         self.log("Write", data)

def write_bytes(self, data):
    '''Write all `data` to the serial connection.'''
    self.serial.write(data)

pylink.link.SerialLink.write = write_bytes

# PATCH ##
# - return data from SerialLink as bytes (without conversion to str)

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

def read_bytes(self, size=None):
    '''Read data from the serial connection. The maximum amount of data
    to be received at once is specified by `size`.'''
    size = size or self.MAX_STRING_SIZE
    # AG: is this the desired behaviour?  Probably not harmful, but I'm not sure.
    #timeout = (timeout or 1) * (self.timeout or 1)
    #self.serial.timeout = timeout
    data = self.serial.read(size)
    #self.serial.timeout = self.timeout
    return data


pylink.link.SerialLink.read = read_bytes



# PATCH #3
# - Simplify _read_one_byte in pakbus (don't do conversion from utf, might break some things)
# 

# This is what was there:
    # def _read_one_byte(self):
    #     '''Read only one byte.'''
    #     data = self.link.read(1)
    #     if is_text(data):
    #         return bytes(data.encode('utf-8'))
    #     else:
    #         return data

def read_one_as_bytes(self):
    '''Read only one byte'''
    data = self.link.read(1)
    if isinstance(data, str):
        print(f'WTF? data is text: {data}')

    return data

pycampbellcr1000.pakbus.PakBus._read_one_byte = read_one_as_bytes

# PATCH #4
# - Avoid using _read_one_byte in pakbus.read

from pycampbellcr1000.pakbus import LOGGER, bytes_to_hex

print(serial.__file__)

def pakbus_readuntil(self):
        '''Receive packet over PakBus.'''
        if False:
            # end of frame character
            EOFM = b'\xbd'
            b1 = self.link._serial.read_until(expected=EOFM, size=4096)
            if b1 == b'':
                LOGGER.error('Timeout waiting for first byte of message body')
                return None

            b2 = self.link._serial.read_until(expected=EOFM, size=4096)
            if b2 == b'':
                LOGGER.error(f'Timeout waiting for message body.  Read: {b1}')
                return None
            # packet (Bytes) is just the bit in between the two b'\xbd' bytes
            packet = b2[:-1]

        if False:

            # this block of code is informed by read_until from pyserial
            while True:
                c = self._read


        if True:
            all_bytes = []
            byte = None
            begin = time.time()

            while byte != b'\xBD':
##                if (byte != None):
##                    LOGGER.info('Read byte: %s' % bytes_to_hex(byte))
                if time.time() - begin > self.link.timeout:
                    return None
                # Read until first \xBD frame character
                byte = self._read_one_byte()
                if byte == b'':
                    LOGGER.error('Timeout waiting for first 0xbd')
                    return None
            while byte == b'\xBD':
                # Read unitl first character other than \xBD
                byte = self._read_one_byte()
                if byte == b'':
                    LOGGER.error('Timeout waiting for first byte of message body')
                    return None

            while byte != b'\xBD':
                # Read until next occurence of \xBD character
                all_bytes.append(byte)
                byte = self._read_one_byte()
                if byte == b'':
                    LOGGER.error('Timeout reading message body')
            packet = b''.join(all_bytes)

        if len(packet) == 0:
            LOGGER.warning("Zero length packet received")
            return self.read()
        
        # Unquote quoted characters
        
        LOGGER.info('Read packet: %s' % bytes_to_hex(packet))
        packet = self.unquote(packet)

        # Calculate signature (should be zero)
        if self.compute_signature(packet):
            LOGGER.error('Check signature : Error')
            return None
        else:
            LOGGER.info('Check signature : OK')
            # Strip last 2 signature bytes and return packet
            return packet[:-2]

pycampbellcr1000.pakbus.PakBus.read = pakbus_readuntil



from pycampbellcr1000 import CR1000


if True:
    if os.name == "nt":
        cr1000 = CR1000.from_url("serial:COM5:115200", timeout=1)  # timeout=2

        #ser = serial.Serial("COM5", baudrate=115200, timeout=10)
        #cr1000 = CR1000(ser)


    else:
        cr1000 = CR1000.from_url("serial://dev/ttyUSB0:115200")

    for ii in range(10):
        tick = time.time()
        tdfdata = cr1000.getfile(".TDF")
        tock = time.time()
        print(f".TDF data length: {len(tdfdata)}, acquired in {tock-tick} sec")

    del(cr1000)

    import sys
    sys.exit()

import binascii
import serial

break_command = b'\xbd\xbd\xbd\xbd\xbd\xbd'

ser = serial.Serial("COM5", baudrate=115200, timeout=10)
ser.flushInput()
ser.flushOutput()
ser.write(break_command)
ser.flushOutput()
time.sleep(0.01)
ser.flushInput()

commands = """BD 90 01 58 02 00 01 08 02 09 01 00 02 07 08 F6 86 BD
BD 90 01 58 02 00 01 08 02 09 02 00 02 07 08 AF 69 BD
BD A0 01 98 02 10 01 08 02 1D 03 00 00 2E 54 44 46 00 00 00 00 00 00 02 00 4E 6D BD
BD A0 01 98 02 10 01 08 02 1D 03 00 00 2E 54 44 46 00 00 00 00 02 00 02 00 0F 53 BD
BD A0 01 98 02 10 01 08 02 1D 03 00 00 2E 54 44 46 00 00 00 00 04 00 02 00 D5 3B BD
BD A0 01 98 02 10 01 08 02 1D 03 00 00 2E 54 44 46 00 00 00 00 06 00 02 00 9B 23 BD
BD A0 01 98 02 10 01 08 02 1D 03 00 00 2E 54 44 46 00 00 00 00 08 00 02 00 61 0B BD
BD A0 01 98 02 10 01 08 02 1D 03 00 00 2E 54 44 46 00 00 00 00 0A 00 02 00 28 F3 BD
BD A0 01 98 02 10 01 08 02 1D 03 00 00 2E 54 44 46 00 00 00 00 0C 00 02 00 EE DB BD
BD A0 01 98 02 10 01 08 02 1D 03 00 00 2E 54 44 46 00 00 00 00 0C 8C 02 00 62 21 BD"""
bin_commands = [binascii.unhexlify(itm) for itm in commands.replace(' ','').split('\n')]

# ser.read()

for bin_command in bin_commands:
    tick = time.time()
    ser.write(bin_command)
    print(f"sending: {binascii.hexlify(bin_command)}")

    time.sleep(0.5)

    header = ser.read_until(b'\xbd')
    other = ser.read_until(b'\xbd')
    print(f"received: {binascii.hexlify(header+other)}")
    tock = time.time()
    print(f"Send+receive took {tock-tick} sec")