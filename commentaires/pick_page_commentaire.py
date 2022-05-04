# -*- coding: utf-8 -*-
"""
@author: Laurent Vaute
email: l.vaute@brgm.fr
copyright: (C) 2019 by BRGM

Module PickEau : partage avec les autres utilisateurs
de commentaires sur la qualité des données téléchargées.
# """


class Pick_Pg_Comment():
    """
    Classe liée à la page 4 de l'objet tabWidget de l'interface de PickEau :
        - partage avec les autres utilisateurs de commentaires sur la qualité des données téléchargées.
    Cette classe prend en paramètres plusieurs instances des modules de PickEau :
        - pickeau_dockwidget.PickEauDockWidget : widget qt contenant les objets de l'interface de PickEau
        - pick_configuration.Pick_Config : fonctions de configuration du plugin PickEau
        - pick_requete.Pick_Req : fonctions d'envoi de requêtes sur les serveurs Hubeau, Sandre, Ades
        - pick_utilitaire.Pick_IO : fonctions de lecture / écriture de fichiers externes
        - pick_utilitaire.Pick_Tools : fonctions utilitaires diverses
    """

    def __init__(self):

        # Définition des attributs de la classe = objets de la classe PickEau passés en paramètre
        # pour éviter les problèmes au rechargement du plugin (https://gis.stackexchange.com/questions/289330/passing-self-when-calling-functions-in-modules-from-other-modules-using-pyqgis)
        # self.__iface = None
        # self.__iface = iface
        # self.__dockwidget = dockwidget
        # self.__test: str = 'test String'
        # button = self.__dockwidget.benButton
        # button.clicked.connect(self.__test2__)
        # self._msg = QMessageBox()

        # self._test = QDialog()
        # #myCom = Ui_gsDockWidget()
        # myCom = Ui_Dialog()
        # myCom.setupUi(self._test)

        # self._test3 = QDialog()
        # myCom2 = Ui_Dialog()
        # myCom2.setupUi(self._test3)

        print('Inside commentaire box')

    # def __test2__(self):
    #     """self """
    #     self.__test = 'test 1'
    #     print(self.__test)
    #     self._test3.show()
        # self._msg.setText("This is a message box")
        # self._msg.show()
