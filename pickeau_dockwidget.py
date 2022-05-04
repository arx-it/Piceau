# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PickEauDockWidget
                                 A QGIS plugin
 L'extension PickEau permet de télécharger automatiquement les chroniques
 de niveau piézométrique et de qualité des eaux souterraines mises à
 disposition par les API Hub'Eau (https://hubeau.eaufrance.fr/).
 PickEau permet ensuite de tracer les chroniques de manière interactive,
 d'afficher leurs statistiques et leurs tendances, et de partager avec
 les autres utilisateurs des commentaires sur la qualité des données. 
 
        begin                : 2019-01-01
        git sha              : $Format:%H$
        copyright            : (C) 2019 by BRGM
        author: Laurent Vaute - l.vaute@brgm.fr
        project manager: Abel Henriot - a.henriot@brgm.fr

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt5 import QtGui, QtWidgets, uic
from PyQt5.QtCore import pyqtSignal

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'pickeau_dockwidget_base.ui'))


class PickEauDockWidget(QtWidgets.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(PickEauDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()
