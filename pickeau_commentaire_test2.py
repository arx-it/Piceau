# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pickeau_commentaire_test2.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(400, 300)
        self.radioButton_3 = QtWidgets.QRadioButton(Form)
        self.radioButton_3.setGeometry(QtCore.QRect(120, 120, 82, 17))
        self.radioButton_3.setObjectName("radioButton_3")
        self.test = QtWidgets.QButtonGroup(Form)
        self.test.setObjectName("test")
        self.test.addButton(self.radioButton_3)
        self.radioButton = QtWidgets.QRadioButton(Form)
        self.radioButton.setGeometry(QtCore.QRect(120, 60, 82, 17))
        self.radioButton.setObjectName("radioButton")
        self.test.addButton(self.radioButton)
        self.radioButton_2 = QtWidgets.QRadioButton(Form)
        self.radioButton_2.setGeometry(QtCore.QRect(120, 90, 82, 17))
        self.radioButton_2.setObjectName("radioButton_2")
        self.test.addButton(self.radioButton_2)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.radioButton_3.setText(_translate("Form", "choix 3"))
        self.radioButton.setText(_translate("Form", "choix1"))
        self.radioButton_2.setText(_translate("Form", "choix 2"))