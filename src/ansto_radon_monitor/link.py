# -*- coding: utf-8 -*-
'''
    pylink.link
    -----------

    :copyright: Copyright 2012 Salem Harrache and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

'''
import socket
import time


# Note: this is the interface from PyLink, but simplified for the intended use-case
#  Pylink: https://github.com/LionelDarras/PyLink

class TCPLink(object):
    '''TCPLink class allows TCP/IP protocol communication with File-like
    API.'''
    def __init__(self, host, port, timeout=20.0):
        self.timeout = timeout
        self.host = socket.gethostbyname(host)
        self.port = port
        self._socket = None
        self._buffer = b""

    def open(self):
        '''Open the socket.'''
        if self._socket is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect(self.address)
            self._socket.setblocking(True)
            self._socket.settimeout(self.timeout)
    
    def write(self, msg: bytes):
        assert(type(msg) == type(b""))
        self.socket.sendall(msg)
        

    def read(self, size: int=1):
        """
        Receive `size` bytes from the network (or buffer)
        
        Note, this is implemented in a somewhat strange manner because, at least on Windows, 
        simply using select or a blocking read with a ~few second timeout appeared to freeze
        the GUI.  This might be caused by an issue elsewhere in the code, see the "sleep" below
        to try troubleshooting the root cause...
        """
        RECV_BUFFER_SIZE=4096

        # try to supply data from the buffer
        data = self._buffer[:size]
        self._buffer = self._buffer[size:]
        t0 = time.time()
        
        while len(data) < size:
            size_remaining = size - len(data)
            try:
                chunk = self.socket.recv(RECV_BUFFER_SIZE)
                if chunk == b'':
                    raise RuntimeError("socket connection broken")

                data = data + chunk[:size_remaining]
                self._buffer = self._buffer + chunk[size_remaining:]                    
                t0 = time.time()
            except TimeoutError:
                if time.time() - t0 > self.timeout:
                    break

        return bytes(data)


    def settimeout(self, timeout):
        self.timeout = timeout

    def close(self):
        '''Close the socket.'''
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    @property
    def socket(self):
        '''Return an opened socket object.'''
        self.open()
        return self._socket

    @property
    def address(self):
        return self.host, self.port