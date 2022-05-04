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

import requests
from functools import partial
from qgis.gui import QgisInterface
from qgis.PyQt.QtWidgets import QDockWidget, QPushButton
from .connexion import Connexion
from .issues import Issues


class Commentaires():

    _apiKey: str
    _mainWidget: QDockWidget
    _iface: QgisInterface

    def __init__(self, mainWidget: QDockWidget, iface):

        self._mainWidget = mainWidget
        self._iface = iface
        self.connexion = Connexion(mainWidget, self)
        self.issues = Issues(mainWidget, iface, self.connexion)

    # fonction executée à la connexion
    def estConnecte(self, connecte: bool):
        self.issues.changeEtatFormulaire(connecte)

    # def getIssues(self):
    #     """
    #     Obtenir la liste des tickets
    #     """
    #     # 100 est la limite maximum
    #     limit: str = '100'
    #     url = 'https://forge-scientifique.brgm-rec.fr/projects/forge-pic-eau/issues.json&limit=' + limit
    #     headers = {'X-Redmine-API-Key': self._apiKey}
    #     r = requests.get(url, headers=headers)
    #     if (r.status_code == 200):
    #         res = r.json()
