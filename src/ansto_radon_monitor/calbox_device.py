from abc import ABC, abstractmethod, abstractproperty
from typing import Dict, Any


class CalboxDevice(ABC):
    """
    This is a synchronous interface to calbox control hardware
    """

    def __init__(self):
        """init should connect to the device"""
        pass

    @abstractmethod
    def flush(self) -> None:
        """Start source-flush pump"""
        pass

    @abstractmethod
    def inject(self, detector_idx: int = 0) -> None:
        """Inject radon from source"""
        pass

    @abstractmethod
    def reset_flush(self) -> None:
        """Stop source-flush pump"""
        pass

    @abstractmethod
    def start_background(self, detector_idx: int = 0) -> None:
        """Put detector in background mode"""
        pass

    @abstractmethod
    def reset_background(self) -> None:
        """Cancel a running background (but leave source flushing if it already is running)"""
        pass

    @abstractmethod
    def reset_calibration(self) -> None:
        """Cancel a running calibration (but leave background-related
        flags unchanged)"""
        pass

    @abstractmethod
    def reset_all(self) -> None:
        """return to idle state"""
        pass

    @abstractproperty
    def analogue_states(self) -> Dict[str, float]:
        channels_dict: Dict[str, float] = {}
        return channels_dict
    
# Commented out so that it can be implemented using a dict attribute
#    @abstractproperty
#    def digital_output_state(self) -> Dict[str, bool]:
#        dio_dict: Dict[str, bool] = {}
#        return dio_dict

    @abstractproperty
    def status(self) -> Dict[str, Any]:
        """generate a human-readable status message based on DIO flags"""
