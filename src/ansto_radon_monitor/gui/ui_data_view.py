# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'data_view.ui'
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
from PySide6.QtWidgets import (QApplication, QHeaderView, QSizePolicy, QSplitter,
    QTableView, QVBoxLayout, QWidget)

class Ui_DataViewForm(object):
    def setupUi(self, DataViewForm):
        if not DataViewForm.objectName():
            DataViewForm.setObjectName(u"DataViewForm")
        DataViewForm.resize(819, 343)
        self.verticalLayout = QVBoxLayout(DataViewForm)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.splitter = QSplitter(DataViewForm)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.pastDataTableView = QTableView(self.splitter)
        self.pastDataTableView.setObjectName(u"pastDataTableView")
        self.splitter.addWidget(self.pastDataTableView)

        self.verticalLayout.addWidget(self.splitter)


        self.retranslateUi(DataViewForm)

        QMetaObject.connectSlotsByName(DataViewForm)
    # setupUi

    def retranslateUi(self, DataViewForm):
        DataViewForm.setWindowTitle(QCoreApplication.translate("DataViewForm", u"Form", None))
    # retranslateUi

