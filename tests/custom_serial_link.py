"""Customised version of SerialLink"""

# The pylink is used by the pycr1000 library for communications.  The upstream 
# version has some problems, so patch in this version until they get fixed
# (e.g. https://github.com/LionelDarras/PyCampbellCR1000/issues/21)

# Code copied from here: https://github.com/SalemHarrache/PyLink/blob/master/pylink/link.py
# Changes made:
#   - avoid changing serial port timeout in "read"
#   - remove workarounds for py2/py3 compatibility (only target py3)
#   - use bytearray to convert from bytes to text-hex (bytearray.fromhex, bytearray.hex)
#   - avoid logging data transfers (logging happens at a higher level in the stack)

import time
import serial


class Link(object):
    '''Abstract base class for all links.'''
    MAX_STRING_SIZE = 4048

    def open(self):
        '''Open the link.'''
        pass

    def close(self):
        '''Close the link.'''
        pass

    def byte_to_hex(self, bytes):
        '''Convert a byte string to it's hex string representation.'''
        s = bytes.hex()
        s_with_spaces = ' '.join(s[i:i+2] for i in range(0, len(s), 2))
        return s_with_spaces

    def __del__(self):
        '''Close link when object is deleted.'''
        self.close()

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.url}>"
    
    @property
    def url(self):
        '''Make a connection url.'''
        return 'Link'



class SerialLink(Link):
    '''SerialLink class allows serial communication with File-like API.
    Possible values for the parameter port:
      - Number: number of device, numbering starts at zero.
      - Device name: depending on operating system.
          e.g. /dev/ttyUSB0 on GNU/Linux or COM3 on Windows.'''
    def __init__(self, port, baudrate=19200, bytesize=8, parity='N',
                 stopbits=1, timeout=1):
        # create serial port object, but don't open it
        self._serial = serial.Serial(None, baudrate=baudrate,
                                         timeout=timeout,
                                         bytesize=bytesize,
                                         parity=parity,
                                         stopbits=stopbits)
        self._serial.port = port

    @property
    def url(self):
        '''Make a connection url.'''
        return f'serial:%s:%d:%d%s%d' % (self.port, self.baudrate,
                                        self.bytesize, self.parity,
                                        self.stopbits)

    def open(self):
        '''Open the serial connection.'''
        if not self._serial.is_open():
            self._serial.open()
            self._serial.reset_output_buffer()

    def settimeout(self, timeout):
        self._serial.timeout = self.timeout

    def close(self):
        '''Close the serial connection.'''
        if self._serial.is_open():
            self._serial.close()

    @property
    def serial(self):
        '''Return an opened serial object.'''
        self.open()
        return self._serial

    def write(self, data):
        '''Write all `data` to the serial connection.'''
        self.serial.write(data)

    def read(self, size=None, timeout=None):
        '''Read data from the serial connection. The maximum amount of data
        to be received at once is specified by `size`. If `is_byte` is True,
        the data will be convert to byte array.'''
        size = size or self.MAX_STRING_SIZE
        data = self.serial.read(size)
        return data
