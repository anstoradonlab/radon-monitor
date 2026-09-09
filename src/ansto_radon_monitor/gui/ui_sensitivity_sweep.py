# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'sensitivity_sweep.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QSizePolicy, QSpinBox, QVBoxLayout,
    QWidget)

class Ui_SensitivitySweepForm(object):
    def setupUi(self, SensitivitySweepForm):
        if not SensitivitySweepForm.objectName():
            SensitivitySweepForm.setObjectName(u"SensitivitySweepForm")
        SensitivitySweepForm.resize(503, 327)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(SensitivitySweepForm.sizePolicy().hasHeightForWidth())
        SensitivitySweepForm.setSizePolicy(sizePolicy)
        self.mainVerticalLayout = QVBoxLayout(SensitivitySweepForm)
        self.mainVerticalLayout.setObjectName(u"mainVerticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.hvSweepGroupBox = QGroupBox(SensitivitySweepForm)
        self.hvSweepGroupBox.setObjectName(u"hvSweepGroupBox")
        sizePolicy.setHeightForWidth(self.hvSweepGroupBox.sizePolicy().hasHeightForWidth())
        self.hvSweepGroupBox.setSizePolicy(sizePolicy)
        self.formLayout = QFormLayout(self.hvSweepGroupBox)
        self.formLayout.setObjectName(u"formLayout")
        self.label_9 = QLabel(self.hvSweepGroupBox)
        self.label_9.setObjectName(u"label_9")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_9)

        self.comboBox = QComboBox(self.hvSweepGroupBox)
        self.comboBox.setObjectName(u"comboBox")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.comboBox)

        self.label_3 = QLabel(self.hvSweepGroupBox)
        self.label_3.setObjectName(u"label_3")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_3)

        self.hvLowSpinBox = QSpinBox(self.hvSweepGroupBox)
        self.hvLowSpinBox.setObjectName(u"hvLowSpinBox")
        self.hvLowSpinBox.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.hvLowSpinBox.setMinimum(100)
        self.hvLowSpinBox.setMaximum(1500)
        self.hvLowSpinBox.setSingleStep(10)
        self.hvLowSpinBox.setValue(800)

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.hvLowSpinBox)

        self.label_4 = QLabel(self.hvSweepGroupBox)
        self.label_4.setObjectName(u"label_4")

        self.formLayout.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_4)

        self.hvHighSpinBox = QSpinBox(self.hvSweepGroupBox)
        self.hvHighSpinBox.setObjectName(u"hvHighSpinBox")
        self.hvHighSpinBox.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.hvHighSpinBox.setMinimum(500)
        self.hvHighSpinBox.setMaximum(1500)
        self.hvHighSpinBox.setSingleStep(10)
        self.hvHighSpinBox.setValue(1000)

        self.formLayout.setWidget(3, QFormLayout.ItemRole.FieldRole, self.hvHighSpinBox)

        self.label_2 = QLabel(self.hvSweepGroupBox)
        self.label_2.setObjectName(u"label_2")

        self.formLayout.setWidget(5, QFormLayout.ItemRole.LabelRole, self.label_2)

        self.hvStepSpinBox = QSpinBox(self.hvSweepGroupBox)
        self.hvStepSpinBox.setObjectName(u"hvStepSpinBox")
        self.hvStepSpinBox.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.hvStepSpinBox.setMinimum(10)
        self.hvStepSpinBox.setMaximum(500)
        self.hvStepSpinBox.setSingleStep(5)
        self.hvStepSpinBox.setValue(50)

        self.formLayout.setWidget(5, QFormLayout.ItemRole.FieldRole, self.hvStepSpinBox)

        self.label_5 = QLabel(self.hvSweepGroupBox)
        self.label_5.setObjectName(u"label_5")

        self.formLayout.setWidget(7, QFormLayout.ItemRole.LabelRole, self.label_5)

        self.hvSecSpinBox = QSpinBox(self.hvSweepGroupBox)
        self.hvSecSpinBox.setObjectName(u"hvSecSpinBox")
        self.hvSecSpinBox.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.hvSecSpinBox.setMinimum(10)
        self.hvSecSpinBox.setMaximum(3600)
        self.hvSecSpinBox.setSingleStep(10)
        self.hvSecSpinBox.setValue(100)

        self.formLayout.setWidget(7, QFormLayout.ItemRole.FieldRole, self.hvSecSpinBox)

        self.noiseCheckBox = QCheckBox(self.hvSweepGroupBox)
        self.noiseCheckBox.setObjectName(u"noiseCheckBox")
        self.noiseCheckBox.setChecked(True)

        self.formLayout.setWidget(8, QFormLayout.ItemRole.FieldRole, self.noiseCheckBox)


        self.horizontalLayout.addWidget(self.hvSweepGroupBox)

        self.statusGroupBox = QGroupBox(SensitivitySweepForm)
        self.statusGroupBox.setObjectName(u"statusGroupBox")
        self.statusGroupBox.setEnabled(False)
        sizePolicy.setHeightForWidth(self.statusGroupBox.sizePolicy().hasHeightForWidth())
        self.statusGroupBox.setSizePolicy(sizePolicy)
        self.statusGroupBox.setFlat(False)
        self.formLayout_2 = QFormLayout(self.statusGroupBox)
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.label = QLabel(self.statusGroupBox)
        self.label.setObjectName(u"label")

        self.formLayout_2.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label)

        self.hvTargetLabel = QLabel(self.statusGroupBox)
        self.hvTargetLabel.setObjectName(u"hvTargetLabel")
        font = QFont()
        font.setPointSize(31)
        self.hvTargetLabel.setFont(font)
        self.hvTargetLabel.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.formLayout_2.setWidget(1, QFormLayout.ItemRole.SpanningRole, self.hvTargetLabel)

        self.label_8 = QLabel(self.statusGroupBox)
        self.label_8.setObjectName(u"label_8")

        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_8)

        self.hvMeasuredLabel = QLabel(self.statusGroupBox)
        self.hvMeasuredLabel.setObjectName(u"hvMeasuredLabel")
        self.hvMeasuredLabel.setFont(font)
        self.hvMeasuredLabel.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.formLayout_2.setWidget(4, QFormLayout.ItemRole.SpanningRole, self.hvMeasuredLabel)

        self.instructionLabel = QLabel(self.statusGroupBox)
        self.instructionLabel.setObjectName(u"instructionLabel")
        palette = QPalette()
        brush = QBrush(QColor(170, 0, 0, 255))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        palette.setBrush(QPalette.ColorGroup.Active, QPalette.ColorRole.WindowText, brush)
        palette.setBrush(QPalette.ColorGroup.Inactive, QPalette.ColorRole.WindowText, brush)
        brush1 = QBrush(QColor(120, 120, 120, 255))
        brush1.setStyle(Qt.BrushStyle.SolidPattern)
        palette.setBrush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, brush1)
        self.instructionLabel.setPalette(palette)
        font1 = QFont()
        font1.setBold(True)
        self.instructionLabel.setFont(font1)
        self.instructionLabel.setAlignment(Qt.AlignCenter)

        self.formLayout_2.setWidget(9, QFormLayout.ItemRole.SpanningRole, self.instructionLabel)

        self.progressBar = QProgressBar(self.statusGroupBox)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setMinimumSize(QSize(207, 0))
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setInvertedAppearance(False)

        self.formLayout_2.setWidget(10, QFormLayout.ItemRole.SpanningRole, self.progressBar)


        self.horizontalLayout.addWidget(self.statusGroupBox)


        self.mainVerticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.startButton = QPushButton(SensitivitySweepForm)
        self.startButton.setObjectName(u"startButton")

        self.horizontalLayout_2.addWidget(self.startButton)

        self.stopButton = QPushButton(SensitivitySweepForm)
        self.stopButton.setObjectName(u"stopButton")

        self.horizontalLayout_2.addWidget(self.stopButton)


        self.mainVerticalLayout.addLayout(self.horizontalLayout_2)


        self.retranslateUi(SensitivitySweepForm)

        QMetaObject.connectSlotsByName(SensitivitySweepForm)
    # setupUi

    def retranslateUi(self, SensitivitySweepForm):
        SensitivitySweepForm.setWindowTitle(QCoreApplication.translate("SensitivitySweepForm", u"Form", None))
        self.hvSweepGroupBox.setTitle(QCoreApplication.translate("SensitivitySweepForm", u" High Voltage Sweep", None))
        self.label_9.setText(QCoreApplication.translate("SensitivitySweepForm", u"Radon Detector", None))
        self.label_3.setText(QCoreApplication.translate("SensitivitySweepForm", u"From", None))
        self.hvLowSpinBox.setSuffix(QCoreApplication.translate("SensitivitySweepForm", u"V", None))
        self.label_4.setText(QCoreApplication.translate("SensitivitySweepForm", u"To", None))
        self.hvHighSpinBox.setSuffix(QCoreApplication.translate("SensitivitySweepForm", u"V", None))
        self.label_2.setText(QCoreApplication.translate("SensitivitySweepForm", u"Step", None))
        self.hvStepSpinBox.setSuffix(QCoreApplication.translate("SensitivitySweepForm", u"V", None))
        self.label_5.setText(QCoreApplication.translate("SensitivitySweepForm", u"Seconds per step", None))
        self.hvSecSpinBox.setSuffix("")
#if QT_CONFIG(tooltip)
        self.noiseCheckBox.setToolTip(QCoreApplication.translate("SensitivitySweepForm", u"Any noisy measurements (ULD counts > 0) are repeated with this option enabled", None))
#endif // QT_CONFIG(tooltip)
        self.noiseCheckBox.setText(QCoreApplication.translate("SensitivitySweepForm", u"Exclude Noisy", None))
        self.statusGroupBox.setTitle(QCoreApplication.translate("SensitivitySweepForm", u"Status", None))
        self.label.setText(QCoreApplication.translate("SensitivitySweepForm", u"High Voltage Target", None))
        self.hvTargetLabel.setText(QCoreApplication.translate("SensitivitySweepForm", u"--- V", None))
        self.label_8.setText(QCoreApplication.translate("SensitivitySweepForm", u"High Voltage Measured", None))
        self.hvMeasuredLabel.setText(QCoreApplication.translate("SensitivitySweepForm", u"--- V", None))
        self.instructionLabel.setText("")
        self.startButton.setText(QCoreApplication.translate("SensitivitySweepForm", u"Start", None))
        self.stopButton.setText(QCoreApplication.translate("SensitivitySweepForm", u"Stop", None))
    # retranslateUi

