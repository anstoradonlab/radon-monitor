# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractScrollArea, QApplication, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QMenu, QMenuBar,
    QPlainTextEdit, QPushButton, QSizePolicy, QSplitter,
    QStatusBar, QTabWidget, QTextBrowser, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(597, 569)
        self.actionLoad_Configuration = QAction(MainWindow)
        self.actionLoad_Configuration.setObjectName(u"actionLoad_Configuration")
        self.actionQuit = QAction(MainWindow)
        self.actionQuit.setObjectName(u"actionQuit")
        self.actionShow_Data = QAction(MainWindow)
        self.actionShow_Data.setObjectName(u"actionShow_Data")
        self.actionViewCalibration = QAction(MainWindow)
        self.actionViewCalibration.setObjectName(u"actionViewCalibration")
        self.actionViewCalibration.setEnabled(False)
        self.actionViewSystemInformation = QAction(MainWindow)
        self.actionViewSystemInformation.setObjectName(u"actionViewSystemInformation")
        self.actionDarkMode = QAction(MainWindow)
        self.actionDarkMode.setObjectName(u"actionDarkMode")
        self.actionDarkMode.setCheckable(True)
        self.actionViewSensitivitySweep = QAction(MainWindow)
        self.actionViewSensitivitySweep.setObjectName(u"actionViewSensitivitySweep")
        self.actionMaintence_Mode = QAction(MainWindow)
        self.actionMaintence_Mode.setObjectName(u"actionMaintence_Mode")
        self.actionMaintence_Mode.setCheckable(True)
        self.actionSync_Output = QAction(MainWindow)
        self.actionSync_Output.setObjectName(u"actionSync_Output")
        self.actionScheduled_Tasks = QAction(MainWindow)
        self.actionScheduled_Tasks.setObjectName(u"actionScheduled_Tasks")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.verticalLayout_3 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.plotSplitter = QSplitter(self.centralwidget)
        self.plotSplitter.setObjectName(u"plotSplitter")
        self.plotSplitter.setOrientation(Qt.Horizontal)
        self.verticalLayoutWidget = QWidget(self.plotSplitter)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.maintenanceModeFrame = QFrame(self.verticalLayoutWidget)
        self.maintenanceModeFrame.setObjectName(u"maintenanceModeFrame")
        self.maintenanceModeFrame.setEnabled(True)
        self.maintenanceModeFrame.setMinimumSize(QSize(0, 41))
        self.horizontalLayout = QHBoxLayout(self.maintenanceModeFrame)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_2 = QLabel(self.maintenanceModeFrame)
        self.label_2.setObjectName(u"label_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(20)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy1)
        self.label_2.setAutoFillBackground(False)
        self.label_2.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)

        self.horizontalLayout.addWidget(self.label_2)

        self.exitMaintenancePushButton = QPushButton(self.maintenanceModeFrame)
        self.exitMaintenancePushButton.setObjectName(u"exitMaintenancePushButton")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(1)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.exitMaintenancePushButton.sizePolicy().hasHeightForWidth())
        self.exitMaintenancePushButton.setSizePolicy(sizePolicy2)

        self.horizontalLayout.addWidget(self.exitMaintenancePushButton)


        self.verticalLayout.addWidget(self.maintenanceModeFrame)

        self.alertFrame = QFrame(self.verticalLayoutWidget)
        self.alertFrame.setObjectName(u"alertFrame")
        self.alertFrame.setFrameShape(QFrame.StyledPanel)
        self.alertFrame.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.alertFrame)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.alertMessage = QLabel(self.alertFrame)
        self.alertMessage.setObjectName(u"alertMessage")

        self.horizontalLayout_3.addWidget(self.alertMessage)


        self.verticalLayout.addWidget(self.alertFrame)

        self.hudTextBrowser = QTextBrowser(self.verticalLayoutWidget)
        self.hudTextBrowser.setObjectName(u"hudTextBrowser")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.hudTextBrowser.sizePolicy().hasHeightForWidth())
        self.hudTextBrowser.setSizePolicy(sizePolicy3)
        self.hudTextBrowser.setMinimumSize(QSize(0, 150))
        self.hudTextBrowser.setBaseSize(QSize(0, 150))
        self.hudTextBrowser.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)

        self.verticalLayout.addWidget(self.hudTextBrowser)

        self.splitter = QSplitter(self.verticalLayoutWidget)
        self.splitter.setObjectName(u"splitter")
        sizePolicy.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setOrientation(Qt.Vertical)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.verticalLayout_2 = QVBoxLayout(self.layoutWidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.tabWidget = QTabWidget(self.layoutWidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setEnabled(True)
        self.tabWidget.setLayoutDirection(Qt.LeftToRight)
        self.tabWidget.setTabPosition(QTabWidget.North)
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.horizontalLayout_2 = QHBoxLayout(self.tab)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label = QLabel(self.tab)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_2.addWidget(self.label)

        self.tabWidget.addTab(self.tab, "")

        self.verticalLayout_2.addWidget(self.tabWidget)

        self.splitter.addWidget(self.layoutWidget)
        self.logArea = QPlainTextEdit(self.splitter)
        self.logArea.setObjectName(u"logArea")
        font = QFont()
        font.setFamilies([u"Monospace"])
        self.logArea.setFont(font)
        self.logArea.setMaximumBlockCount(50000)
        self.splitter.addWidget(self.logArea)

        self.verticalLayout.addWidget(self.splitter)

        self.plotSplitter.addWidget(self.verticalLayoutWidget)

        self.verticalLayout_3.addWidget(self.plotSplitter)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 597, 21))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuView = QMenu(self.menubar)
        self.menuView.setObjectName(u"menuView")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuView.menuAction())
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

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"ANSTO RDM", None))
        self.actionLoad_Configuration.setText(QCoreApplication.translate("MainWindow", u"Load Configuration", None))
        self.actionQuit.setText(QCoreApplication.translate("MainWindow", u"Quit", None))
        self.actionShow_Data.setText(QCoreApplication.translate("MainWindow", u"Show Data", None))
        self.actionViewCalibration.setText(QCoreApplication.translate("MainWindow", u"Calibration", None))
        self.actionViewSystemInformation.setText(QCoreApplication.translate("MainWindow", u"System Information", None))
        self.actionDarkMode.setText(QCoreApplication.translate("MainWindow", u"Dark Mode", None))
        self.actionViewSensitivitySweep.setText(QCoreApplication.translate("MainWindow", u"Sensitivity Sweep", None))
        self.actionMaintence_Mode.setText(QCoreApplication.translate("MainWindow", u"Maintence Mode", None))
        self.actionSync_Output.setText(QCoreApplication.translate("MainWindow", u"Sync Output Files", None))
        self.actionScheduled_Tasks.setText(QCoreApplication.translate("MainWindow", u"Scheduled Tasks", None))
#if QT_CONFIG(tooltip)
        self.label_2.setToolTip(QCoreApplication.translate("MainWindow", u"Maintenance mode indicates that the detector is undergoing maintenance and measurements should be disregarded.", None))
#endif // QT_CONFIG(tooltip)
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"\u26a0\ufe0f Maintenance Mode Active", None))
        self.exitMaintenancePushButton.setText(QCoreApplication.translate("MainWindow", u"Exit Maintenance Mode", None))
        self.alertMessage.setText(QCoreApplication.translate("MainWindow", u"\u26a0\ufe0f Calibration Unit Active", None))
        self.hudTextBrowser.setHtml(QCoreApplication.translate("MainWindow", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><title>template table</title><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:'MS Shell Dlg 2'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p align=\"center\" style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">...waiting for data...</p></body></html>", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"No data", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("MainWindow", u"No data to display", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuView.setTitle(QCoreApplication.translate("MainWindow", u"View", None))
    # retranslateUi

