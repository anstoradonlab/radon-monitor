# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/main_window.ui'
#
# Created by: PyQt5 UI code generator 5.15.11
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(597, 569)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.plotSplitter = QtWidgets.QSplitter(self.centralwidget)
        self.plotSplitter.setOrientation(QtCore.Qt.Horizontal)
        self.plotSplitter.setObjectName("plotSplitter")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.plotSplitter)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.maintenanceModeFrame = QtWidgets.QFrame(self.verticalLayoutWidget)
        self.maintenanceModeFrame.setEnabled(True)
        self.maintenanceModeFrame.setMinimumSize(QtCore.QSize(0, 41))
        self.maintenanceModeFrame.setObjectName("maintenanceModeFrame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.maintenanceModeFrame)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_2 = QtWidgets.QLabel(self.maintenanceModeFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(20)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setAutoFillBackground(False)
        self.label_2.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.exitMaintenancePushButton = QtWidgets.QPushButton(self.maintenanceModeFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.exitMaintenancePushButton.sizePolicy().hasHeightForWidth())
        self.exitMaintenancePushButton.setSizePolicy(sizePolicy)
        self.exitMaintenancePushButton.setObjectName("exitMaintenancePushButton")
        self.horizontalLayout.addWidget(self.exitMaintenancePushButton)
        self.verticalLayout.addWidget(self.maintenanceModeFrame)
        self.alertFrame = QtWidgets.QFrame(self.verticalLayoutWidget)
        self.alertFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.alertFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.alertFrame.setObjectName("alertFrame")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.alertFrame)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.alertMessage = QtWidgets.QLabel(self.alertFrame)
        self.alertMessage.setObjectName("alertMessage")
        self.horizontalLayout_3.addWidget(self.alertMessage)
        self.verticalLayout.addWidget(self.alertFrame)
        self.hudTextBrowser = QtWidgets.QTextBrowser(self.verticalLayoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.hudTextBrowser.sizePolicy().hasHeightForWidth())
        self.hudTextBrowser.setSizePolicy(sizePolicy)
        self.hudTextBrowser.setMinimumSize(QtCore.QSize(0, 150))
        self.hudTextBrowser.setBaseSize(QtCore.QSize(0, 150))
        self.hudTextBrowser.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustIgnored)
        self.hudTextBrowser.setObjectName("hudTextBrowser")
        self.verticalLayout.addWidget(self.hudTextBrowser)
        self.splitter = QtWidgets.QSplitter(self.verticalLayoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setObjectName("splitter")
        self.layoutWidget = QtWidgets.QWidget(self.splitter)
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.tabWidget = QtWidgets.QTabWidget(self.layoutWidget)
        self.tabWidget.setEnabled(True)
        self.tabWidget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.tabWidget.setTabPosition(QtWidgets.QTabWidget.North)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.tab)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtWidgets.QLabel(self.tab)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.tabWidget.addTab(self.tab, "")
        self.verticalLayout_2.addWidget(self.tabWidget)
        self.logArea = QtWidgets.QPlainTextEdit(self.splitter)
        font = QtGui.QFont()
        font.setFamily("Monospace")
        self.logArea.setFont(font)
        self.logArea.setMaximumBlockCount(50000)
        self.logArea.setObjectName("logArea")
        self.verticalLayout.addWidget(self.splitter)
        self.verticalLayout_3.addWidget(self.plotSplitter)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 597, 21))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuView = QtWidgets.QMenu(self.menubar)
        self.menuView.setObjectName("menuView")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionLoad_Configuration = QtWidgets.QAction(MainWindow)
        self.actionLoad_Configuration.setObjectName("actionLoad_Configuration")
        self.actionQuit = QtWidgets.QAction(MainWindow)
        self.actionQuit.setObjectName("actionQuit")
        self.actionShow_Data = QtWidgets.QAction(MainWindow)
        self.actionShow_Data.setObjectName("actionShow_Data")
        self.actionViewCalibration = QtWidgets.QAction(MainWindow)
        self.actionViewCalibration.setEnabled(False)
        self.actionViewCalibration.setObjectName("actionViewCalibration")
        self.actionViewSystemInformation = QtWidgets.QAction(MainWindow)
        self.actionViewSystemInformation.setObjectName("actionViewSystemInformation")
        self.actionDarkMode = QtWidgets.QAction(MainWindow)
        self.actionDarkMode.setCheckable(True)
        self.actionDarkMode.setObjectName("actionDarkMode")
        self.actionViewSensitivitySweep = QtWidgets.QAction(MainWindow)
        self.actionViewSensitivitySweep.setObjectName("actionViewSensitivitySweep")
        self.actionMaintence_Mode = QtWidgets.QAction(MainWindow)
        self.actionMaintence_Mode.setCheckable(True)
        self.actionMaintence_Mode.setObjectName("actionMaintence_Mode")
        self.actionSync_Output = QtWidgets.QAction(MainWindow)
        self.actionSync_Output.setObjectName("actionSync_Output")
        self.actionScheduled_Tasks = QtWidgets.QAction(MainWindow)
        self.actionScheduled_Tasks.setObjectName("actionScheduled_Tasks")
        self.menuFile.addAction(self.actionLoad_Configuration)
        self.menuFile.addAction(self.actionSync_Output)
        self.menuFile.addAction(self.actionShow_Data)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionMaintence_Mode)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionQuit)
        self.menuView.addAction(self.actionViewCalibration)
        self.menuView.addAction(self.actionViewSystemInformation)
        self.menuView.addAction(self.actionViewSensitivitySweep)
        self.menuView.addSeparator()
        self.menuView.addAction(self.actionScheduled_Tasks)
        self.menuView.addSeparator()
        self.menuView.addAction(self.actionDarkMode)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuView.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "ANSTO RDM"))
        self.label_2.setToolTip(_translate("MainWindow", "Maintenance mode indicates that the detector is undergoing maintenance and measurements should be disregarded."))
        self.label_2.setText(_translate("MainWindow", "⚠️ Maintenance Mode Active"))
        self.exitMaintenancePushButton.setText(_translate("MainWindow", "Exit Maintenance Mode"))
        self.alertMessage.setText(_translate("MainWindow", "⚠️ Calibration Unit Active"))
        self.hudTextBrowser.setHtml(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><title>template table</title><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p align=\"center\" style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">...waiting for data...</p></body></html>"))
        self.label.setText(_translate("MainWindow", "No data"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "No data to display"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuView.setTitle(_translate("MainWindow", "View"))
        self.actionLoad_Configuration.setText(_translate("MainWindow", "Load Configuration"))
        self.actionQuit.setText(_translate("MainWindow", "Quit"))
        self.actionShow_Data.setText(_translate("MainWindow", "Show Data"))
        self.actionViewCalibration.setText(_translate("MainWindow", "Calibration"))
        self.actionViewSystemInformation.setText(_translate("MainWindow", "System Information"))
        self.actionDarkMode.setText(_translate("MainWindow", "Dark Mode"))
        self.actionViewSensitivitySweep.setText(_translate("MainWindow", "Sensitivity Sweep"))
        self.actionMaintence_Mode.setText(_translate("MainWindow", "Maintence Mode"))
        self.actionSync_Output.setText(_translate("MainWindow", "Sync Output Files"))
        self.actionScheduled_Tasks.setText(_translate("MainWindow", "Scheduled Tasks"))
