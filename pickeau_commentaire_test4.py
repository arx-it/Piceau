# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pickeau_commentaire_test4.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_gsDockWidget(object):
    def setupUi(self, gsDockWidget):
        gsDockWidget.setObjectName("gsDockWidget")
        gsDockWidget.resize(400, 300)

        self.retranslateUi(gsDockWidget)
        QtCore.QMetaObject.connectSlotsByName(gsDockWidget)

    def retranslateUi(self, gsDockWidget):
        _translate = QtCore.QCoreApplication.translate
        gsDockWidget.setWindowTitle(_translate("gsDockWidget", "gsDockWidget"))

from qgsdockwidget import QgsDockWidget
