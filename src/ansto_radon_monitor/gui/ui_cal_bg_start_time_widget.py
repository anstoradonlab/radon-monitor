# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/cal_bg_start_time_widget.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_CalBgStartWidget(object):
    def setupUi(self, CalBgStartWidget):
        CalBgStartWidget.setObjectName("CalBgStartWidget")
        CalBgStartWidget.resize(389, 154)
        self.gridLayout = QtWidgets.QGridLayout(CalBgStartWidget)
        self.gridLayout.setObjectName("gridLayout")
        self.titleLabel = QtWidgets.QLabel(CalBgStartWidget)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.titleLabel.setFont(font)
        self.titleLabel.setObjectName("titleLabel")
        self.gridLayout.addWidget(self.titleLabel, 0, 0, 1, 2)
        self.label_4 = QtWidgets.QLabel(CalBgStartWidget)
        self.label_4.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 1, 0, 1, 1)
        self.firstScheduledCalibrationDateTimeEdit = QtWidgets.QDateTimeEdit(CalBgStartWidget)
        self.firstScheduledCalibrationDateTimeEdit.setEnabled(True)
        self.firstScheduledCalibrationDateTimeEdit.setProperty("showGroupSeparator", False)
        self.firstScheduledCalibrationDateTimeEdit.setDateTime(QtCore.QDateTime(QtCore.QDate(2000, 1, 2), QtCore.QTime(6, 0, 0)))
        self.firstScheduledCalibrationDateTimeEdit.setCurrentSection(QtWidgets.QDateTimeEdit.HourSection)
        self.firstScheduledCalibrationDateTimeEdit.setCalendarPopup(True)
        self.firstScheduledCalibrationDateTimeEdit.setTimeSpec(QtCore.Qt.UTC)
        self.firstScheduledCalibrationDateTimeEdit.setObjectName("firstScheduledCalibrationDateTimeEdit")
        self.gridLayout.addWidget(self.firstScheduledCalibrationDateTimeEdit, 1, 1, 1, 1)
        self.label_10 = QtWidgets.QLabel(CalBgStartWidget)
        self.label_10.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_10.setObjectName("label_10")
        self.gridLayout.addWidget(self.label_10, 2, 0, 1, 1)
        self.calLocalTimeLabel = QtWidgets.QLabel(CalBgStartWidget)
        self.calLocalTimeLabel.setObjectName("calLocalTimeLabel")
        self.gridLayout.addWidget(self.calLocalTimeLabel, 2, 1, 1, 1)
        self.label_8 = QtWidgets.QLabel(CalBgStartWidget)
        self.label_8.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_8.setObjectName("label_8")
        self.gridLayout.addWidget(self.label_8, 3, 0, 1, 1)
        self.firstScheduledBackgroundDateTimeEdit = QtWidgets.QDateTimeEdit(CalBgStartWidget)
        self.firstScheduledBackgroundDateTimeEdit.setEnabled(True)
        self.firstScheduledBackgroundDateTimeEdit.setCurrentSection(QtWidgets.QDateTimeEdit.HourSection)
        self.firstScheduledBackgroundDateTimeEdit.setCalendarPopup(True)
        self.firstScheduledBackgroundDateTimeEdit.setTimeSpec(QtCore.Qt.UTC)
        self.firstScheduledBackgroundDateTimeEdit.setObjectName("firstScheduledBackgroundDateTimeEdit")
        self.gridLayout.addWidget(self.firstScheduledBackgroundDateTimeEdit, 3, 1, 1, 1)
        self.label_11 = QtWidgets.QLabel(CalBgStartWidget)
        self.label_11.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_11.setObjectName("label_11")
        self.gridLayout.addWidget(self.label_11, 4, 0, 1, 1)
        self.bgLocalTimeLabel = QtWidgets.QLabel(CalBgStartWidget)
        self.bgLocalTimeLabel.setObjectName("bgLocalTimeLabel")
        self.gridLayout.addWidget(self.bgLocalTimeLabel, 4, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(225, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.gridLayout.addItem(spacerItem, 5, 1, 1, 1)

        self.retranslateUi(CalBgStartWidget)
        QtCore.QMetaObject.connectSlotsByName(CalBgStartWidget)

    def retranslateUi(self, CalBgStartWidget):
        _translate = QtCore.QCoreApplication.translate
        CalBgStartWidget.setWindowTitle(_translate("CalBgStartWidget", "Form"))
        self.titleLabel.setText(_translate("CalBgStartWidget", "Detector 1: [detector name]"))
        self.label_4.setText(_translate("CalBgStartWidget", "First calibration"))
        self.firstScheduledCalibrationDateTimeEdit.setDisplayFormat(_translate("CalBgStartWidget", "yyyy-MM-dd hh:mm UTC"))
        self.label_10.setText(_translate("CalBgStartWidget", "(In local time)"))
        self.calLocalTimeLabel.setText(_translate("CalBgStartWidget", "---"))
        self.label_8.setText(_translate("CalBgStartWidget", "First background"))
        self.firstScheduledBackgroundDateTimeEdit.setDisplayFormat(_translate("CalBgStartWidget", "yyyy-MM-dd hh:mm UTC"))
        self.label_11.setText(_translate("CalBgStartWidget", "(In local time)"))
        self.bgLocalTimeLabel.setText(_translate("CalBgStartWidget", "---"))

