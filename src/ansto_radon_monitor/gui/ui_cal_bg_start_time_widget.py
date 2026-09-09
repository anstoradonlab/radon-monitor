# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'cal_bg_start_time_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QDateTimeEdit, QGridLayout, QLabel,
    QSizePolicy, QSpacerItem, QWidget)

class Ui_CalBgStartWidget(object):
    def setupUi(self, CalBgStartWidget):
        if not CalBgStartWidget.objectName():
            CalBgStartWidget.setObjectName(u"CalBgStartWidget")
        CalBgStartWidget.resize(389, 154)
        self.gridLayout = QGridLayout(CalBgStartWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.titleLabel = QLabel(CalBgStartWidget)
        self.titleLabel.setObjectName(u"titleLabel")
        font = QFont()
        font.setBold(True)
        self.titleLabel.setFont(font)

        self.gridLayout.addWidget(self.titleLabel, 0, 0, 1, 2)

        self.label_4 = QLabel(CalBgStartWidget)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.label_4, 1, 0, 1, 1)

        self.firstScheduledCalibrationDateTimeEdit = QDateTimeEdit(CalBgStartWidget)
        self.firstScheduledCalibrationDateTimeEdit.setObjectName(u"firstScheduledCalibrationDateTimeEdit")
        self.firstScheduledCalibrationDateTimeEdit.setEnabled(True)
        self.firstScheduledCalibrationDateTimeEdit.setProperty(u"showGroupSeparator", False)
        self.firstScheduledCalibrationDateTimeEdit.setDateTime(QDateTime(QDate(2000, 1, 2), QTime(6, 0, 0)))
        self.firstScheduledCalibrationDateTimeEdit.setCurrentSection(QDateTimeEdit.HourSection)
        self.firstScheduledCalibrationDateTimeEdit.setCalendarPopup(True)
        self.firstScheduledCalibrationDateTimeEdit.setTimeSpec(Qt.UTC)

        self.gridLayout.addWidget(self.firstScheduledCalibrationDateTimeEdit, 1, 1, 1, 1)

        self.label_10 = QLabel(CalBgStartWidget)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.label_10, 2, 0, 1, 1)

        self.calLocalTimeLabel = QLabel(CalBgStartWidget)
        self.calLocalTimeLabel.setObjectName(u"calLocalTimeLabel")

        self.gridLayout.addWidget(self.calLocalTimeLabel, 2, 1, 1, 1)

        self.label_8 = QLabel(CalBgStartWidget)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.label_8, 3, 0, 1, 1)

        self.firstScheduledBackgroundDateTimeEdit = QDateTimeEdit(CalBgStartWidget)
        self.firstScheduledBackgroundDateTimeEdit.setObjectName(u"firstScheduledBackgroundDateTimeEdit")
        self.firstScheduledBackgroundDateTimeEdit.setEnabled(True)
        self.firstScheduledBackgroundDateTimeEdit.setCurrentSection(QDateTimeEdit.HourSection)
        self.firstScheduledBackgroundDateTimeEdit.setCalendarPopup(True)
        self.firstScheduledBackgroundDateTimeEdit.setTimeSpec(Qt.UTC)

        self.gridLayout.addWidget(self.firstScheduledBackgroundDateTimeEdit, 3, 1, 1, 1)

        self.label_11 = QLabel(CalBgStartWidget)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.label_11, 4, 0, 1, 1)

        self.bgLocalTimeLabel = QLabel(CalBgStartWidget)
        self.bgLocalTimeLabel.setObjectName(u"bgLocalTimeLabel")

        self.gridLayout.addWidget(self.bgLocalTimeLabel, 4, 1, 1, 1)

        self.verticalSpacer = QSpacerItem(225, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.gridLayout.addItem(self.verticalSpacer, 5, 1, 1, 1)


        self.retranslateUi(CalBgStartWidget)

        QMetaObject.connectSlotsByName(CalBgStartWidget)
    # setupUi

    def retranslateUi(self, CalBgStartWidget):
        CalBgStartWidget.setWindowTitle(QCoreApplication.translate("CalBgStartWidget", u"Form", None))
        self.titleLabel.setText(QCoreApplication.translate("CalBgStartWidget", u"Detector 1: [detector name]", None))
        self.label_4.setText(QCoreApplication.translate("CalBgStartWidget", u"First calibration", None))
        self.firstScheduledCalibrationDateTimeEdit.setDisplayFormat(QCoreApplication.translate("CalBgStartWidget", u"yyyy-MM-dd hh:mm UTC", None))
        self.label_10.setText(QCoreApplication.translate("CalBgStartWidget", u"(In local time)", None))
        self.calLocalTimeLabel.setText(QCoreApplication.translate("CalBgStartWidget", u"---", None))
        self.label_8.setText(QCoreApplication.translate("CalBgStartWidget", u"First background", None))
        self.firstScheduledBackgroundDateTimeEdit.setDisplayFormat(QCoreApplication.translate("CalBgStartWidget", u"yyyy-MM-dd hh:mm UTC", None))
        self.label_11.setText(QCoreApplication.translate("CalBgStartWidget", u"(In local time)", None))
        self.bgLocalTimeLabel.setText(QCoreApplication.translate("CalBgStartWidget", u"---", None))
    # retranslateUi

