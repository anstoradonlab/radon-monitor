# A dialog which shows the status of currently scheduled tasks.
# This does not use QT Designer


from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets, QtCore
from PyQt5 import uic
from PyQt5.QtCore import Qt
import pyqtgraph as pg

import sys
import datetime


class CalibrationHistoryWidget(QtWidgets.QWidget):
    
    def __init__(self, *args, **kwargs):
        super(CalibrationHistoryWidget, self).__init__(*args, **kwargs)
        self.init_layout()
        self.init_graph()
        self.draw_graph()

    def init_layout(self):
        self.layout = QtWidgets.QVBoxLayout(self)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(QtWidgets.QLabel(text="Detector:"))
        self._cb_detector = QtWidgets.QComboBox()
        hbox.addWidget(self._cb_detector)
        self.layout.addLayout(hbox)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(QtWidgets.QLabel(text="Type of event:"))
        self._cb_kind = QtWidgets.QComboBox()
        self._cb_kind.addItems(["Calibration", "Background"])
        # TODO: signal, combobox.currentTextChanged.connect(self.text_changed)

        hbox.addWidget(self._cb_kind)
        self.layout.addLayout(hbox)
        
        self._win = pg.GraphicsLayoutWidget(show=True, title="Sensitivity Sweep")
        self.layout.addWidget(self._win)


    def init_graph(self):
        """Initial construction of the plots"""
        self._p1 = self._win.addPlot(
            row=0, col=0,
        )
        self._p1.setLabel("left", "LLD", units="counts per 30-min")
        self._p2.setLabel("bottom", "Time since start of event", units="hours")
        self._p2 = self._win.addPlot(row=1, col=0, axisItems={"bottom": pg.DateAxisItem(utcOffset=0)})
        self._p2.setLabel("left", "LLD", units="cps")
        self._s1 = []
        self._s2 = []

        self._clickedBrush=pg.mkBrush(200, 200, 255, 120)
        self._clickedPen = pg.mkPen('b', width=2)
        self._lastClicked = []


        

    def draw_graph(self):
        """Draw or refresh the plots"""
        n = 10

        # the approach pre-renders a single spot, and then adds lots of duplicates
        s1 = pg.ScatterPlotItem(size=15, pen=pg.mkPen(None), brush=pg.mkBrush(128, 128, 128, 120))
        pos_x = [datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(days=ii) for ii in range(n)]
        pos_x = [itm.timestamp() for itm in pos_x]
        pos_y = [ii for ii in range(n)]
        # data is used as an index into the calibration event index
        spots = [{'pos': [pos_x[ii], pos_y[ii]], 'data': ii} for ii in range(n)]
        s1.addPoints(spots)
        self._scatter = s1
        self._p2.addItem(s1)
        s1.sigClicked.connect(self.clicked)

        self.set_selected(n-1)
        self.update_selected()

    

    def clicked(self, _plot, points):
        # restrict to just one point
        points = points[:1]
        index = points[0].data()
        self._selected_event_idx = index

        # redraw
        self.update_selected()

    
    def set_selected(self, idx):
        self._selected_event_idx = idx

    def update_selected(self):
        """update plots to reflect a change in which event is selected"""
        p = self._scatter.points()[self._selected_event_idx]
        for old_p in self._lastClicked:
            old_p.resetPen()
            old_p.resetBrush()
        p.setPen(self._clickedPen)
        p.setBrush(self._clickedBrush)
        self._lastClicked = [p]

    
    def update_data(self):
        """Refresh the dialog state from datastore"""
        pass

    def initialise(self):
        """Initialise dialog, after configuration has changed"""
        pass
    

class CalibrationHistoryDialog(QtWidgets.QDialog):

    def __init__(self, *args, **kwargs):
        super(CalibrationHistoryDialog, self).__init__(*args, **kwargs)

        self.setWindowTitle("Calibration History")

        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)
        self.mainwidget = CalibrationHistoryWidget()
        layout.addWidget(self.mainwidget)

        closeButton = QtWidgets.QPushButton(self)
        closeButton.setText("Close")
        closeButton.clicked.connect(self.close)
        layout.addWidget(closeButton)

        self.setSizeGripEnabled(True)


    def update_configuration(self):
        # or whatever function name is used elsewhere
        # (respond to a change in configuration)
        pass
