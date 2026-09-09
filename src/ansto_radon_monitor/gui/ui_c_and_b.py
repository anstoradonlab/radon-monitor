# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'c_and_b.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QSpinBox, QVBoxLayout,
    QWidget)

class Ui_CAndBForm(object):
    def setupUi(self, CAndBForm):
        if not CAndBForm.objectName():
            CAndBForm.setObjectName(u"CAndBForm")
        CAndBForm.resize(560, 710)
        self.verticalLayout = QVBoxLayout(CAndBForm)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.groupBox = QGroupBox(CAndBForm)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.startLaterCheckBox = QCheckBox(self.groupBox)
        self.startLaterCheckBox.setObjectName(u"startLaterCheckBox")

        self.gridLayout_2.addWidget(self.startLaterCheckBox, 4, 1, 1, 1)

        self.startStopPushButton = QPushButton(self.groupBox)
        self.startStopPushButton.setObjectName(u"startStopPushButton")
        self.startStopPushButton.setCheckable(True)

        self.gridLayout_2.addWidget(self.startStopPushButton, 8, 1, 1, 1)

        self.calbgDateTimeEdit = QDateTimeEdit(self.groupBox)
        self.calbgDateTimeEdit.setObjectName(u"calbgDateTimeEdit")
        self.calbgDateTimeEdit.setEnabled(False)
        self.calbgDateTimeEdit.setMinimumDateTime(QDateTime(QDate(1752, 9, 13), QTime(17, 0, 0)))
        self.calbgDateTimeEdit.setMinimumTime(QTime(17, 0, 0))
        self.calbgDateTimeEdit.setCurrentSection(QDateTimeEdit.YearSection)
        self.calbgDateTimeEdit.setCalendarPopup(True)
        self.calbgDateTimeEdit.setTimeSpec(Qt.UTC)

        self.gridLayout_2.addWidget(self.calbgDateTimeEdit, 5, 1, 1, 1)

        self.label_14 = QLabel(self.groupBox)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_14, 2, 0, 1, 1)

        self.label_13 = QLabel(self.groupBox)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_13, 4, 0, 1, 1)

        self.calbgLocalTimeLabel = QLabel(self.groupBox)
        self.calbgLocalTimeLabel.setObjectName(u"calbgLocalTimeLabel")

        self.gridLayout_2.addWidget(self.calbgLocalTimeLabel, 6, 1, 1, 1)

        self.label_12 = QLabel(self.groupBox)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_12, 5, 0, 1, 1)

        self.label_15 = QLabel(self.groupBox)
        self.label_15.setObjectName(u"label_15")
        self.label_15.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_15, 6, 0, 1, 1)

        self.operationTypeComboBox = QComboBox(self.groupBox)
        self.operationTypeComboBox.setObjectName(u"operationTypeComboBox")

        self.gridLayout_2.addWidget(self.operationTypeComboBox, 2, 1, 1, 1)


        self.verticalLayout_3.addWidget(self.groupBox)


        self.verticalLayout.addLayout(self.verticalLayout_3)

        self.groupBox_2 = QGroupBox(CAndBForm)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_3 = QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.cal_bg_start_times_layout = QVBoxLayout()
        self.cal_bg_start_times_layout.setObjectName(u"cal_bg_start_times_layout")

        self.gridLayout_3.addLayout(self.cal_bg_start_times_layout, 2, 0, 1, 2)

        self.enableScheduleButton = QPushButton(self.groupBox_2)
        self.enableScheduleButton.setObjectName(u"enableScheduleButton")
        self.enableScheduleButton.setCheckable(True)

        self.gridLayout_3.addWidget(self.enableScheduleButton, 3, 1, 1, 1)

        self.label_5 = QLabel(self.groupBox_2)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_5, 0, 0, 1, 1)

        self.label_9 = QLabel(self.groupBox_2)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout_3.addWidget(self.label_9, 1, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.calibrationIntervalSpinBox = QSpinBox(self.groupBox_2)
        self.calibrationIntervalSpinBox.setObjectName(u"calibrationIntervalSpinBox")
        self.calibrationIntervalSpinBox.setMinimum(0)
        self.calibrationIntervalSpinBox.setValue(28)

        self.horizontalLayout.addWidget(self.calibrationIntervalSpinBox)

        self.calUnitsComboBox = QComboBox(self.groupBox_2)
        self.calUnitsComboBox.setObjectName(u"calUnitsComboBox")

        self.horizontalLayout.addWidget(self.calUnitsComboBox)


        self.gridLayout_3.addLayout(self.horizontalLayout, 0, 1, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.backgroundIntervalSpinBox = QSpinBox(self.groupBox_2)
        self.backgroundIntervalSpinBox.setObjectName(u"backgroundIntervalSpinBox")
        self.backgroundIntervalSpinBox.setMinimum(0)
        self.backgroundIntervalSpinBox.setValue(84)

        self.horizontalLayout_2.addWidget(self.backgroundIntervalSpinBox)

        self.backgroundUnitsComboBox = QComboBox(self.groupBox_2)
        self.backgroundUnitsComboBox.setObjectName(u"backgroundUnitsComboBox")

        self.horizontalLayout_2.addWidget(self.backgroundUnitsComboBox)


        self.gridLayout_3.addLayout(self.horizontalLayout_2, 1, 1, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_2)

        self.groupBox_3 = QGroupBox(CAndBForm)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout = QGridLayout(self.groupBox_3)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label = QLabel(self.groupBox_3)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.flushSpinBox = QSpinBox(self.groupBox_3)
        self.flushSpinBox.setObjectName(u"flushSpinBox")
        self.flushSpinBox.setMaximum(9999)
        self.flushSpinBox.setValue(12)

        self.gridLayout.addWidget(self.flushSpinBox, 0, 1, 1, 1)

        self.label_2 = QLabel(self.groupBox_3)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.injectSpinBox = QSpinBox(self.groupBox_3)
        self.injectSpinBox.setObjectName(u"injectSpinBox")
        self.injectSpinBox.setMaximum(9999)
        self.injectSpinBox.setValue(6)

        self.gridLayout.addWidget(self.injectSpinBox, 1, 1, 1, 1)

        self.label_3 = QLabel(self.groupBox_3)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.backgroundSpinBox = QSpinBox(self.groupBox_3)
        self.backgroundSpinBox.setObjectName(u"backgroundSpinBox")
        self.backgroundSpinBox.setMaximum(9999)
        self.backgroundSpinBox.setValue(24)

        self.gridLayout.addWidget(self.backgroundSpinBox, 2, 1, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_3)

        self.scheduleEngagedLabel = QLabel(CAndBForm)
        self.scheduleEngagedLabel.setObjectName(u"scheduleEngagedLabel")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scheduleEngagedLabel.sizePolicy().hasHeightForWidth())
        self.scheduleEngagedLabel.setSizePolicy(sizePolicy)
        palette = QPalette()
        brush = QBrush(QColor(170, 0, 0, 255))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        palette.setBrush(QPalette.ColorGroup.Active, QPalette.ColorRole.WindowText, brush)
        palette.setBrush(QPalette.ColorGroup.Inactive, QPalette.ColorRole.WindowText, brush)
        brush1 = QBrush(QColor(120, 120, 120, 255))
        brush1.setStyle(Qt.BrushStyle.SolidPattern)
        palette.setBrush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, brush1)
        self.scheduleEngagedLabel.setPalette(palette)
        font = QFont()
        font.setBold(True)
        self.scheduleEngagedLabel.setFont(font)
        self.scheduleEngagedLabel.setAlignment(Qt.AlignCenter)

        self.verticalLayout.addWidget(self.scheduleEngagedLabel)


        self.retranslateUi(CAndBForm)

        QMetaObject.connectSlotsByName(CAndBForm)
    # setupUi

    def retranslateUi(self, CAndBForm):
        CAndBForm.setWindowTitle(QCoreApplication.translate("CAndBForm", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("CAndBForm", u"Once-off", None))
#if QT_CONFIG(tooltip)
        self.startLaterCheckBox.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.startLaterCheckBox.setText(QCoreApplication.translate("CAndBForm", u"start later", None))
        self.startStopPushButton.setText(QCoreApplication.translate("CAndBForm", u"Start", None))
        self.calbgDateTimeEdit.setDisplayFormat(QCoreApplication.translate("CAndBForm", u"yyyy-MM-dd hh:mm UTC", None))
        self.label_14.setText(QCoreApplication.translate("CAndBForm", u"Type of operation:", None))
        self.label_13.setText(QCoreApplication.translate("CAndBForm", u"Timing:", None))
        self.calbgLocalTimeLabel.setText(QCoreApplication.translate("CAndBForm", u"---", None))
        self.label_12.setText(QCoreApplication.translate("CAndBForm", u" Start time:", None))
        self.label_15.setText(QCoreApplication.translate("CAndBForm", u"(In local Time):", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("CAndBForm", u"Schedule", None))
        self.enableScheduleButton.setText(QCoreApplication.translate("CAndBForm", u"Enable Schedule", None))
        self.label_5.setText(QCoreApplication.translate("CAndBForm", u"Calibration interval", None))
        self.label_9.setText(QCoreApplication.translate("CAndBForm", u"Background interval", None))
        self.calibrationIntervalSpinBox.setSuffix("")
        self.backgroundIntervalSpinBox.setSuffix("")
        self.groupBox_3.setTitle(QCoreApplication.translate("CAndBForm", u"Parameters", None))
        self.label.setText(QCoreApplication.translate("CAndBForm", u"Flush duration:", None))
        self.flushSpinBox.setSuffix(QCoreApplication.translate("CAndBForm", u" hours", None))
        self.label_2.setText(QCoreApplication.translate("CAndBForm", u"Inject duration:", None))
        self.injectSpinBox.setSuffix(QCoreApplication.translate("CAndBForm", u" hours", None))
        self.label_3.setText(QCoreApplication.translate("CAndBForm", u"Background duration:", None))
        self.backgroundSpinBox.setSuffix(QCoreApplication.translate("CAndBForm", u" hours", None))
        self.scheduleEngagedLabel.setText("")
    # retranslateUi

