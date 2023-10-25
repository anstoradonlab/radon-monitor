# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/data_view.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_DataViewForm(object):
    def setupUi(self, DataViewForm):
        DataViewForm.setObjectName("DataViewForm")
        DataViewForm.resize(819, 343)
        self.verticalLayout = QtWidgets.QVBoxLayout(DataViewForm)
        self.verticalLayout.setObjectName("verticalLayout")
        self.splitter = QtWidgets.QSplitter(DataViewForm)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.pastDataTableView = QtWidgets.QTableView(self.splitter)
        self.pastDataTableView.setObjectName("pastDataTableView")
        self.verticalLayout.addWidget(self.splitter)

        self.retranslateUi(DataViewForm)
        QtCore.QMetaObject.connectSlotsByName(DataViewForm)

    def retranslateUi(self, DataViewForm):
        _translate = QtCore.QCoreApplication.translate
        DataViewForm.setWindowTitle(_translate("DataViewForm", "Form"))

