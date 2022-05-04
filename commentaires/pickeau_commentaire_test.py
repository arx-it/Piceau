# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pickeau_commentaire_test.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(400, 300)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(40, 250, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.radioButton = QtWidgets.QRadioButton(Dialog)
        self.radioButton.setGeometry(QtCore.QRect(170, 50, 82, 17))
        self.radioButton.setObjectName("radioButton")
        self.choixCommentaire = QtWidgets.QButtonGroup(Dialog)
        self.choixCommentaire.setObjectName("choixCommentaire")
        self.choixCommentaire.addButton(self.radioButton)
        self.radioButton_2 = QtWidgets.QRadioButton(Dialog)
        self.radioButton_2.setGeometry(QtCore.QRect(170, 80, 82, 17))
        self.radioButton_2.setObjectName("radioButton_2")
        self.choixCommentaire.addButton(self.radioButton_2)
        self.radioButton_3 = QtWidgets.QRadioButton(Dialog)
        self.radioButton_3.setGeometry(QtCore.QRect(170, 110, 82, 17))
        self.radioButton_3.setObjectName("radioButton_3")
        self.choixCommentaire.addButton(self.radioButton_3)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.radioButton.setText(_translate("Dialog", "choix1"))
        self.radioButton_2.setText(_translate("Dialog", "choix 2"))
        self.radioButton_3.setText(_translate("Dialog", "choix 3"))

