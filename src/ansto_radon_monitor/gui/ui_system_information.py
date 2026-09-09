# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'system_information.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QLabel, QPushButton, QSizePolicy, QTextBrowser,
    QVBoxLayout, QWidget)

class Ui_SystemInformationForm(object):
    def setupUi(self, SystemInformationForm):
        if not SystemInformationForm.objectName():
            SystemInformationForm.setObjectName(u"SystemInformationForm")
        SystemInformationForm.resize(347, 697)
        self.verticalLayout = QVBoxLayout(SystemInformationForm)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.notLoggingLabel = QLabel(SystemInformationForm)
        self.notLoggingLabel.setObjectName(u"notLoggingLabel")
        self.notLoggingLabel.setEnabled(True)
        palette = QPalette()
        brush = QBrush(QColor(170, 0, 0, 255))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        palette.setBrush(QPalette.ColorGroup.Active, QPalette.ColorRole.WindowText, brush)
        palette.setBrush(QPalette.ColorGroup.Inactive, QPalette.ColorRole.WindowText, brush)
        brush1 = QBrush(QColor(120, 120, 120, 255))
        brush1.setStyle(Qt.BrushStyle.SolidPattern)
        palette.setBrush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, brush1)
        self.notLoggingLabel.setPalette(palette)
        font = QFont()
        font.setBold(True)
        self.notLoggingLabel.setFont(font)
        self.notLoggingLabel.setAlignment(Qt.AlignCenter)

        self.verticalLayout.addWidget(self.notLoggingLabel)

        self.stopLoggingButton = QPushButton(SystemInformationForm)
        self.stopLoggingButton.setObjectName(u"stopLoggingButton")
        self.stopLoggingButton.setCheckable(True)

        self.verticalLayout.addWidget(self.stopLoggingButton)

        self.groupBox = QGroupBox(SystemInformationForm)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.downloadButton = QPushButton(self.groupBox)
        self.downloadButton.setObjectName(u"downloadButton")

        self.gridLayout_2.addWidget(self.downloadButton, 6, 1, 1, 2)

        self.queryButton = QPushButton(self.groupBox)
        self.queryButton.setObjectName(u"queryButton")

        self.gridLayout_2.addWidget(self.queryButton, 4, 1, 1, 2)

        self.serialPortComboBox = QComboBox(self.groupBox)
        self.serialPortComboBox.setObjectName(u"serialPortComboBox")

        self.gridLayout_2.addWidget(self.serialPortComboBox, 3, 1, 1, 2)

        self.label_4 = QLabel(self.groupBox)
        self.label_4.setObjectName(u"label_4")
        font1 = QFont()
        font1.setBold(True)
        font1.setItalic(False)
        self.label_4.setFont(font1)
        self.label_4.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_4, 8, 1, 1, 2)

        self.timeSyncButton = QPushButton(self.groupBox)
        self.timeSyncButton.setObjectName(u"timeSyncButton")

        self.gridLayout_2.addWidget(self.timeSyncButton, 7, 1, 1, 2)

        self.sendProgramButton = QPushButton(self.groupBox)
        self.sendProgramButton.setObjectName(u"sendProgramButton")

        self.gridLayout_2.addWidget(self.sendProgramButton, 9, 1, 1, 2)

        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 0, 1, 1, 1)

        self.dataLoggerTextBrowser = QTextBrowser(self.groupBox)
        self.dataLoggerTextBrowser.setObjectName(u"dataLoggerTextBrowser")
        self.dataLoggerTextBrowser.setTabChangesFocus(True)

        self.gridLayout_2.addWidget(self.dataLoggerTextBrowser, 5, 1, 1, 2)


        self.verticalLayout.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(SystemInformationForm)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.queryLabjackButton = QPushButton(self.groupBox_2)
        self.queryLabjackButton.setObjectName(u"queryLabjackButton")

        self.verticalLayout_2.addWidget(self.queryLabjackButton)

        self.labjackTextBrowser = QTextBrowser(self.groupBox_2)
        self.labjackTextBrowser.setObjectName(u"labjackTextBrowser")
        self.labjackTextBrowser.setTabChangesFocus(True)

        self.verticalLayout_2.addWidget(self.labjackTextBrowser)


        self.verticalLayout.addWidget(self.groupBox_2)

        self.label_2 = QLabel(SystemInformationForm)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setWordWrap(True)

        self.verticalLayout.addWidget(self.label_2)


        self.retranslateUi(SystemInformationForm)

        QMetaObject.connectSlotsByName(SystemInformationForm)
    # setupUi

    def retranslateUi(self, SystemInformationForm):
        SystemInformationForm.setWindowTitle(QCoreApplication.translate("SystemInformationForm", u"Form", None))
        self.notLoggingLabel.setText("")
        self.stopLoggingButton.setText(QCoreApplication.translate("SystemInformationForm", u"Stop Logging", None))
        self.groupBox.setTitle(QCoreApplication.translate("SystemInformationForm", u"Data Loggers", None))
        self.downloadButton.setText(QCoreApplication.translate("SystemInformationForm", u"Retrieve Data Logger Program", None))
        self.queryButton.setText(QCoreApplication.translate("SystemInformationForm", u"Query Port", None))
        self.label_4.setText(QCoreApplication.translate("SystemInformationForm", u"Caution: clears data logger memory", None))
        self.timeSyncButton.setText(QCoreApplication.translate("SystemInformationForm", u"Force Clock Sync", None))
        self.sendProgramButton.setText(QCoreApplication.translate("SystemInformationForm", u"Send New Datalogger Program", None))
        self.label.setText(QCoreApplication.translate("SystemInformationForm", u"Serial ports:", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("SystemInformationForm", u"Lab Jacks", None))
        self.queryLabjackButton.setText(QCoreApplication.translate("SystemInformationForm", u"Query Labjacks", None))
        self.label_2.setText(QCoreApplication.translate("SystemInformationForm", u"Run tests to identify Campbell Scientific data loggers and Lab Jacks.  If there are other instruments connected to this computer over serial ports or using other Lab Jacks then the tests here could interfere with them. Logging from the radon detector needs to be suspended before the tests can run.", None))
    # retranslateUi

