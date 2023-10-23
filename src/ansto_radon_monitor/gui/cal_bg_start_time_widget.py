# -*- coding: utf-8 -*-
import datetime

from PyQt5 import QtWidgets
from ui_cal_bg_start_time_widget import Ui_CalBgStartWidget


def t_into_utc(t):
    """converts a datetime (t) without any timezone info into
    the same t but identified as utc"""
    t = datetime.datetime(*t.timetuple()[:6], tzinfo=datetime.timezone.utc)
    return t


class CalBgStartWidget(QtWidgets.QWidget, Ui_CalBgStartWidget):
    def __init__(self, sequence_number: int, detector_name: str, *args, **kwargs):
        """Create a widget which displays calender entries for the
        first cal and bg times, along with local time conversion

        Parent code should be able interact with this only via creation,
        destruction, and reading the two properties:

            widget.cal_start_time
            widget.bg_start_time

        which return the user-entered cal and bg start times in UTC

        Parameters
        ----------
        sequence_number : integer
            The detector number (1, 2, ...)
        detector_name : str
            The detector name
        """
        super(CalBgStartWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self._sequence_number = sequence_number
        self._detector_name = detector_name
        self._finalise_ui()
        self._connect_signals()

    def _finalise_ui(self):
        self.titleLabel.setText(
            f"Detector {self._sequence_number}: {self._detector_name}"
        )

    def _connect_signals(self):
        # need to keep local time versions of times in sync
        # with UTC input
        self.firstScheduledCalibrationDateTimeEdit.dateTimeChanged.connect(
            self._update_local_times
        )
        self.firstScheduledBackgroundDateTimeEdit.dateTimeChanged.connect(
            self._update_local_times
        )

    def _update_local_times(self):
        """
        Read the time in the UTC boxes and write Local Time to the
        Local time displays
        """
        t0_background = (
            self.firstScheduledBackgroundDateTimeEdit.dateTime().toPyDateTime()
        )
        tstr = str(t_into_utc(t0_background).astimezone())
        self.bgLocalTimeLabel.setText(tstr)
        t0_cal = self.firstScheduledCalibrationDateTimeEdit.dateTime().toPyDateTime()
        tstr = str(t_into_utc(t0_cal).astimezone())
        self.calLocalTimeLabel.setText(tstr)

    @property
    def cal_start_time(self):
        t = self.firstScheduledCalibrationDateTimeEdit.dateTime().toPyDateTime()
        return t_into_utc(t)

    @cal_start_time.setter
    def cal_start_time(self, t):
        self.firstScheduledCalibrationDateTimeEdit.setDateTime(t)
        self._update_local_times()

    @property
    def bg_start_time(self):
        t = self.firstScheduledBackgroundDateTimeEdit.dateTime().toPyDateTime()
        return t_into_utc(t)

    @bg_start_time.setter
    def bg_start_time(self, t):
        self.firstScheduledBackgroundDateTimeEdit.setDateTime(t)
        self._update_local_times()
