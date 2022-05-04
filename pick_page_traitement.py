# -*- coding: utf-8 -*-
"""
@author: Laurent Vaute
email: l.vaute@brgm.fr
copyright: (C) 2019 by BRGM

Module de PickEau : traitement par lot de chroniques =
téléchargement sur Hubeau de statistiques et de tendances.
"""

from PyQt5.QtWidgets import QDockWidget, QAction, QFileDialog, QMessageBox
from qgis.core import *
from qgis.gui import QgsProjectionSelectionWidget

class Pick_Pg_Proc():
    """
    Classe liée à la page 3 de l'objet tabWidget de l'interface de PickEau :
        - traitements en lot des chroniques : statistiques, tendances.
    Cette classe prend en paramètres plusieurs instances des modules de PickEau :
        - pickeau_dockwidget.PickEauDockWidget : widget qt contenant les objets de l'interface de PickEau
        - pick_configuration.Pick_Config : fonctions de configuration du plugin PickEau
        - pick_requete.Pick_Req : fonctions d'envoi de requêtes sur les serveurs Hubeau, Sandre, Ades
        - pick_utilitaire.Pick_IO : fonctions de lecture / écriture de fichiers externes
        - pick_utilitaire.Pick_Tools : fonctions utilitaires diverses
    """

    def __init__(self, iface, dockwidget, pio, ptools, pconfig, preq):

        # Définition des attributs de la classe = objets de la classe PickEau passés en paramètre
        self.iface = None   # pour éviter les problèmes au rechargement du plugin (https://gis.stackexchange.com/questions/289330/passing-self-when-calling-functions-in-modules-from-other-modules-using-pyqgis)
        self.iface = iface
        self.pconfig = pconfig
        self.preq = preq
        self.pio = pio
        self.ptools = ptools
        self.dockwidget = dockwidget

        # Condition utilisée pour le test de certaines fonctions de la classe lorsque l'accès aux objets de l'interface est impossible
        if not self.dockwidget is None:

            pass

    def fonction_a_venir(self):

        pass


if __name__ == '__main__':

    print("")
    print("---------------------------------")
    print("  Test de la classe Pick_Pg_Proc")
    print("---------------------------------")
    print("")

    import pick_utilitaire
    import pick_configuration
    import pick_requete

    # Instanciations de classes PickEau externes au module
    pio = pick_utilitaire.Pick_IO()
    ptools = pick_utilitaire.Pick_Tools()
    pconfig = pick_configuration.Pick_Config(pio, ptools)
    preq = pick_requete.Pick_Req(pio, ptools)

    # Instanciation de la classe
    pproc = Pick_Pg_Proc(None, pconfig, preq, pio, ptools)

    print("variable : ", "")
