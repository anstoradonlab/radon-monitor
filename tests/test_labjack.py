import ctypes
import logging
import math
import os
import struct
import time
import threading
from typing import List

logformat = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d %(threadName)s] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=logformat)
_logger = logging.getLogger()



import u12




def bool_list_to_int(a):
    """
    convert a list of boolean flags into an integer-based bitfield

    The boolean flags toggle the bits from the LSB,
    i.e. a[0] corresponds to the least significant bit,
    so the list written out is in the reverse order to the binary
    representation printed using bin(bitfield)
    """
    bitfield = 0
    for ii in range(len(a)):
        bitfield = bitfield | int(a[ii]) << ii
    return bitfield


def int_to_bool_list(bitfield, numbits):
    """
    Convert an integer-based bitfield into a list of boolean flags
    """
    a = [False for ii in range(numbits)]
    for ii in range(numbits):
        a[ii] = bool(bitfield >> ii & 1)
    return a


class LabjackWrapper:
    """Wrapper for the labjack interface.

    Purpose is to provide a specialized version of the interface, which only includes
    the functions needed for our calibration system.

    There are multiple APIs to access the LabJack, so the use of this wrapper means
    that we'll be able to switch later if needed.

    Only DIO ports 0-5 are used in our setup.

    """

    def __init__(self, labjack_id=-1, serialNumber=None):
        try:
            if serialNumber is not None:
                self.device = u12.U12(debug=False, serialNumber=serialNumber)
            else:
                self.device = u12.U12(id=labjack_id, debug=False)
            self.max_channel = 5
            try:
                self.reset_dio()
            except Exception as ex:
                _logger.error(f"Error calling reset_dio(): {ex}")
                raise
        except Exception as ex:
            _logger.error(f"Unable to connect to labjack because of error: {ex}")

    def set_digital_outputs(self, state: List[bool]):
        """
        Set all digital outputs

        All digitial IO lines are set to output mode

        Channels are set to high or low depending on the values of state.
        Channel 0 is set from state[0], channel 1 from state[1], etc.

        state must have length of 16
        """
        _logger.debug(f"Setting digital outputs to: {state}")
        d = self.device
        assert len(state) == 16
        if os.name == "nt":
            # the IO lines are unused - but we need to set something
            trisIO = 0
            stateIO = 0
            stateD = bool_list_to_int(state)
            # trisD 1-valued bits to signal digital output
            all_high = 2 ** 16 - 1
            d.digitalIO(
                trisD=all_high,
                stateD=stateD,
                updateDigital=1,
                trisIO=trisIO,
                stateIO=stateIO,
            )
        else:
            D15toD8States = bool_list_to_int(state[8:16])
            D7toD0States = bool_list_to_int(state[:8])

            status = d.rawDIO(
                D15toD8Directions=0,
                D7toD0Directions=0,
                D15toD8States=D15toD8States,
                D7toD0States=D7toD0States,
                IO3toIO0DirectionsAndStates=0,
                UpdateDigital=True,
            )

    def reset_dio(self):
        """Sets output to zero on all channels while also configuring all DIO channels as output"""
        _logger.debug(f"Setting all digital outputs to zero")
        d = self.device
        # eDigitalOut doesn't work on Windows, so use the low-level commands
        if os.name == "nt":
            # there are 16 DIO channels, here is a bit flag of 16 1s
            all_high = 2 ** 16 - 1
            d.digitalIO(trisD=all_high, stateD=0, updateDigital=1, trisIO=0, stateIO=0)
        else:
            all_high_byte = 2 ** 8 - 1
            # Args:
            # D15toD8Directions, A byte where 0 = Output, 1 = Input for D15-8
            # D7toD0Directions, A byte where 0 = Output, 1 = Input for D7-0
            # D15toD8States, A byte where 0 = Low, 1 = High for D15-8
            # D7toD0States, A byte where 0 = Low, 1 = High for D7-0
            # IO3toIO0DirectionsAndStates, Bits 7-4: Direction, 3-0: State
            # UpdateDigital, True if you want to update the IO/D line. False to
            #             False to just read their values.
            status = d.rawDIO(
                D15toD8Directions=0,
                D7toD0Directions=0,
                D15toD8States=0,
                D7toD0States=0,
                IO3toIO0DirectionsAndStates=0,
                UpdateDigital=True,
            )

    def set_dio(self, channel, state):
        """Set one DIO channel to 1 or 0"""
        _logger.debug(f"Setting one digital output, channel: {channel}, state: {state}")
        d = self.device
        ret = d.eDigitalOut(channel, state)
        # TODO: raise an exception instead (may have lost connection to labjack)
        assert ret["idnum"] == d.id

    @property
    def dio_states(self):
        """
        Read the DIO states
        """
        _logger.debug(f"Reading DIO states")
        d = self.device
        if os.name == "nt":
            status = d.digitalIO(
                updateDigital=0,
            )
            direction = int_to_bool_list(status["trisD"], 16)
            level = int_to_bool_list(status["stateD"], 16)
        else:
            status = d.rawDIO(UpdateDigital=False)
            direction = int_to_bool_list(
                status["D7toD0Directions"], 8
            ) + int_to_bool_list(status["D15toD8Directions"], 8)
            level = int_to_bool_list(status["D7toD0States"], 8) + int_to_bool_list(
                status["D15toD8States"], 8
            )

        return level, direction

        # this would have the side-effect of setting all channels to input
        # if this function is needed, it will need to use rawDIO on linux, digitialIO on
        # windows
        # refer to https://labjack.com/forums/u12/liblabjackusbso-undefined-symbol-digitalio

        # TODO: this should be implemented because sometimes (Weybourne) we've noticed
        # the DIO state changing without being told to.

        # TODO: Here's some notes for the rawDIO on linux:
        # import u12
        # d = u12.U12()
        # state = d.rawDIO()
        # # remove the latch states (so we can send 'state' back to the function as **state)
        # state.pop('D15toD8OutputLatchStates')
        # state.pop('D7toD0OutputLatchStates')
        # # remove the IO data
        # state.pop('IO3toIO0States')
        # # set one of the channels
        # k = 'D0'
        # direction = 0 # 0 is output
        # signal = 1 # 0 is low voltage, 1 is high voltage
        # setattr(state['D7toD0Directions'], k, direction)
        # setattr(state['D7toD0States'], k, signal)
        # d.rawDIO(**state, UpdateDigital=True)

    @property
    def analogue_states(self, retries=3):
        """Read analog channels 0 and 1"""
        _logger.debug(f"Reading analog channels")
        d = self.device
        try:
            a_in = d.aiSample(channels=[0,1], numChannels=2)
            # a_in is now something like: {'idnum': -1,
            #    'stateIO': 0,
            #    'overVoltage': 999,  # 0 - not over voltage, >0 - over voltage 
            #    'voltages': [2.5, 1.9677734375]}
        except Exception as ex:
            _logger.error(f"Error reading from labjack analogue channels: {ex}")
            if retries > 0:
                time.sleep(0.1)
                self.analogue_states(self, retries=retries-1)
            else:
                return [None, None]
            
        if a_in['overVoltage'] > 0:
            _logger.error(f"One of the Labjack analog channels is over voltage")
        # remember - special value of -1 means 'talk to any labjack'
        if d.id != -1 and a_in["idnum"] != d.id:
            _logger.error(
                f"Labjack reports IDNUM={a_in['idnum']} but we expected {d.id}"
            )

        return a_in["voltages"]

    @property
    def serial_number(self):
        _logger.debug(f"Reading labjack serial number")
        d = self.device
        # serial no is four bytes at address 0
        if os.name == "nt":
            serial_no_bytes = d.readMem(0)
            serial_no = struct.unpack(">I", struct.pack("BBBB", *serial_no_bytes))[0]
        else:
            r = d.rawReadRAM()
            # >>> print(r)
            # {'DataByte3': 5, 'DataByte2': 246, 'DataByte1': 139, 'DataByte0': 170}
            serial_no_bytes = [
                r["DataByte3"],
                r["DataByte2"],
                r["DataByte1"],
                r["DataByte0"],
            ]
            serial_no = struct.unpack(">I", struct.pack("BBBB", *serial_no_bytes))[0]
        return serial_no


def test_ljw():
    ljw = LabjackWrapper()

    print(f'serial number: {ljw.serial_number}')

    print('resetting DIO')

    ljw.reset_dio()

    print(f'Digital: {ljw.dio_states}')

    print(f'Analog: {ljw.analogue_states}')

    print(f"current thread: {threading.currentThread()}")


for ii in range(1):
    print('Testing in main thread')

    t = threading.Thread(target=test_ljw)
    t.start()

    #test_ljw()
    time.sleep(0.1)

    print("Testing in new thread")
    t.join()
    print("Back in main thread... complete.")


print(f"current thread: {threading.currentThread()}")