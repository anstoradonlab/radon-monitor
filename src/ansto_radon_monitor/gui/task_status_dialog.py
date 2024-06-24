# A dialog which shows the status of currently scheduled tasks.
# This does not use QT Designer


from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets, QtCore
from PyQt5 import uic
from PyQt5.QtCore import Qt

import sys
import datetime


class TableModel(QtCore.QAbstractTableModel):
    def __init__(self, data):
        super(TableModel, self).__init__()
        if len(data)>0:
            self._column_names = list(data[0])
            self._data = data[1:]
        else:
            self._column_names = []
            self._data = []


    def data(self, index, role):
        if role == Qt.DisplayRole:
            # Get the raw value
            value = self._data[index.row()][index.column()]

            # Perform per-type checks and render accordingly.
            if isinstance(value, datetime.datetime):
                # Render date and time
                return value.strftime("%Y-%m-%d %H:%M:%S")

            if isinstance(value, float):
                # Render float to 2 dp
                return "%.2f" % value

            if isinstance(value, str):
                # do nothing
                return value
            
            if isinstance(value, datetime.timedelta):
                newvalue = value - datetime.timedelta(seconds=0, microseconds=value.microseconds)
                return str(newvalue)
            
            if value is None:
                return ""

            # Default (anything not captured above: e.g. int)
            return str(value)
    
    def rowCount(self, index):
        # The length of the outer list.
        return len(self._data)

    def columnCount(self, index):
        # The following takes the first dict, and returns
        # the length (only works if all rows are an equal length)
        return len(self._column_names)

    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._column_names[section])

            if orientation == Qt.Vertical:
                # use row number here
                return str(section)
    
    def update_data(self, new_data):
        if len(new_data) == 0 and len(self._data) == 0:
            # no-op
            return
        self.beginResetModel()
        if len(new_data)>0:
            self._column_names = list(new_data[0])
            self._data = new_data[1:]
        else:
            self._column_names = []
            self._data = []
        self.endResetModel()
    


class TaskStatusWidget(QtWidgets.QWidget):
    
    def __init__(self, data, *args, **kwargs):
        super(TaskStatusWidget, self).__init__(*args, **kwargs)

        self.data = data
        self.model = TableModel(data)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self.layout)
        
        self.tableView = QtWidgets.QTableView(self)
        self.tableView.setModel(self.model)
        self.tableView.verticalHeader().hide()
        self.layout.addWidget(self.tableView)
    
    def update_data(self, data):
        self.model.update_data(data)
    

class TaskStatusDialog(QtWidgets.QDialog):

    def __init__(self, *args, **kwargs):
        super(TaskStatusDialog, self).__init__(*args, **kwargs)

        self.setWindowTitle("Scheduled tasks")

        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)
        self.table = TaskStatusWidget(data=[])
        layout.addWidget(self.table)

        closeButton = QtWidgets.QPushButton(self)
        closeButton.setText("Close")
        closeButton.clicked.connect(self.close)
        layout.addWidget(closeButton)

        self.setSizeGripEnabled(True)
        self.resize(800,400)

    def update_data(self, data):
        self.table.update_data(data)    

