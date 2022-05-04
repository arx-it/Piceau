import os
import json
from functools import partial
from qgis.gui import QgsMapCanvas
from qgis.core import QgsRectangle, QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform
from ..pick_utilitaire import Pick_IO
from PyQt5.QtWidgets import QDockWidget, QPushButton, QMessageBox


class ZoneEtude:
    """Classe pour zoomer sur/modifier la zone d'étude de la carte par défaut.
    """

    def __init__(self, map: QgsMapCanvas, plugin_dir: str, dockwidget: QDockWidget):
        """Constructor.
        :param map: Carte Qgis.
        :type map: QgsMapCanvas

        :param plugin_dir: Chemin absolu du plugin
        :type plugin_dir: str

        :param dockwidget: Widget principal du plugin
        :type dockwidget: QDockWidget
        """

        self._map: QgsMapCanvas = map
        self._plugin_dir = plugin_dir
        self.utilitaire = Pick_IO()
        self._coords = ["xMin", "yMin", "xMax", "yMax"]

        # extent par defaut
        self.__setDefaultExtent()

        # zoomer sur l'entendu par defaut
        self.__goZoneEtude()

        # clicked ajoute un argument "checked", partial permet de passer self en argument
        dockwidget.btn_centrer.clicked.connect(partial(self.__goZoneEtude, self))

        button = dockwidget.definir_zone_etude
        button.clicked.connect(partial(self.__sauvegardeDefaultExtent, self))

    def __goZoneEtude(self, checked=False):
        """Aller à la zone d'étude par defaut

        :param checked: (Optionnel) Valeur envoyée lors du click du bouton, si le bouton est "checkable". Désactivé ici.
        :type checked: bool
        """
        self._map.setExtent(self.default_extent, False)

    def __setDefaultExtent(self):
        """
        Définis la valeur default_extent de la classe. On regarde d'abord si une valeur est définie par l'utilisateur
        dans le fichier user_config. Si valeur absente ou invalide, on lit l'emprise par defaut dans le fichier default_config
        """

        file_path = 'configs/user_config.json'
        abs_path = os.path.join(self._plugin_dir, file_path)

        # on regarde si le fichier user_config exist et s'il est valide
        if (os.path.isfile(abs_path)):
            config: dict = self.utilitaire.lire_fichier_json(abs_path)
            if (self.__configEstValide(config) is False):
                config = self.__getDefaultConfig()
        else:
            config = self.__getDefaultConfig()

        extent: QgsRectangle = QgsRectangle(config['zone_etude']['xMin'],
                                            config['zone_etude']['yMin'],
                                            config['zone_etude']['xMax'],
                                            config['zone_etude']['yMax'])

        # reprojecte l'etendu dans la projection de la carte (etendu est enregistre en WGS 84)
        project = QgsProject.instance()
        crsSrc = project.crs().postgisSrid()
        extent_reprojete = self.__reprojectionExtent(extent, 4326, crsSrc, project)

        self.default_extent = extent_reprojete

    def __getDefaultConfig(self):
        """
        Lis le fichier de configuration default_config.json.

        :returns: contient les xMin, yMin, xMax, yMax de la zone d'étude.
        :rtype: dict
        """
        file_path = 'configs/default_config.json'
        abs_path = os.path.join(self._plugin_dir, file_path)
        config: dict = self.utilitaire.lire_fichier_json(abs_path)
        return config

    def __configEstValide(self, config: dict):
        """Vérifie que la configuration du fichier json contient bien des coordonnées x,y min max pour definir une emprise

        :param config: Configuration lu dans les fichiers de configuration
        :type config: dict

        returns: Booléen renseignant une configuration valide ou non
        :rtype: bool
        """

        isValid = True
        for coord in self._coords:
            if (coord not in config['zone_etude']):
                isValid = False
        return isValid

    def __sauvegardeDefaultExtent(self, checked=False):
        """Créé et affiche la boite de dialog pour confirmer ou annuler l'enregistrement de la nouvelle emprise par defaut

        :param checked: (Optionnel)-- Valeur envoyée lors du click du bouton, si le bouton est "checkable". Désactivé ici
        :type checked: bool
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Emprise:")
        msg.setText(" AAVoulez-vous définir l'étendue actuelle de la carte comme zone d'étude")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        reponseUtilisateur = msg.exec_()

        if (reponseUtilisateur == QMessageBox.Yes):
            self.__sauvegardeDefaultExtentInFile()

    def __sauvegardeDefaultExtentInFile(self):
        """
        Créé ou modifie le fichier user_config avec les valeurs de l'emprise de la carte. Les coordonnees sont enregistrées
        en WGS84 (EPSG: 4326)
        """
        extent: QgsRectangle = self._map.extent()

        # lire projection en cours de la carte
        project = QgsProject.instance()
        crsSrc = project.crs().postgisSrid()

        # enregistrer les coordonnees vers le wgs 84
        extent_reprojetee = self.__reprojectionExtent(extent, crsSrc, 4326, project)

        # coordonnees de la l'étendue actuelle de la carte
        file_path = 'configs/user_config.json'
        abs_path = os.path.join(self._plugin_dir, file_path)

        if (os.path.isfile(abs_path)):
            res: dict = self.utilitaire.lire_fichier_json(abs_path)
        else:
            res = {'zone_etude': {}}

        # coordonnees de la l'étendue actuelle de la carte
        res['zone_etude']['xMin'] = extent_reprojetee.xMinimum()
        res['zone_etude']['yMin'] = extent_reprojetee.yMinimum()
        res['zone_etude']['xMax'] = extent_reprojetee.xMaximum()
        res['zone_etude']['yMax'] = extent_reprojetee.yMaximum()

        self.utilitaire.ecrire_fichier_json(res, abs_path)
        self.__setDefaultExtent()

    def __reprojectionExtent(self, extent: QgsRectangle, epsgSource: str, epsgDest: str, context: QgsProject):
        """
        Reprojete une etendue

        :param extent: Etendue à reprojeter.
        :type extent: QgsRectangle

        :param epsgSource: ESPG id d'origine de la couche.
        :type epsgSource: str

        :param epsgDest: ESPG id de sortie de la couche.
        :type epsgDest: str

        :param context: project Qgis.
        :type context: QgsProject

        :returns: retourne l'etendue reprojetee.
        :rtype: QgsProject
        """
        # Création des projections à partir des EPSG Ids
        crsSource = QgsCoordinateReferenceSystem(epsgSource)
        crsDest = QgsCoordinateReferenceSystem(epsgDest)

        # transformation des coordonnées
        transformer = QgsCoordinateTransform(crsSource, crsDest, context)
        extentReprojetee = transformer.transform(extent)

        return extentReprojetee
