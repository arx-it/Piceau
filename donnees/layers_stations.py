from qgis.gui import QgisInterface
from qgis.core import QgsMapLayer, QgsFeature, QgsField
from qgis.PyQt.QtWidgets import QDockWidget


class StationsLayers():

    _mainWidget: QDockWidget
    _iface: QgisInterface

    def __init__(self, mainWidget: QDockWidget, iface: QgisInterface):
        self._mainWidget = mainWidget
        self._iface = iface

    def activeLayerEstCouchePiezometre(self) -> QgsMapLayer:
        """
        Vérifie que la couche courante est la couche piezometre et la retourne si c'est le cas

        :return: Couche courante
        :rtype: QgsMapLayer
        """
        couche_courante: QgsMapLayer = self._iface.activeLayer()
        if (couche_courante):
            if(couche_courante.name() == "Stations_Piézomètres"):
                return couche_courante
            else:
                return None
        else:
            return None

    def getBssStations(self, layer: QgsMapLayer, champRecherche: str) -> list:
        """
        Créé une liste des valeurs du champ recherché d'une couche

        :param layer: Couche où rechercher les valeurs
        :type layer: QgsMapLayer

        :param champRecherche: Champ recherché
        :type champRecherche: QgsMapLayer

        :return: Liste des valeurs du champ recherché
        :rtype: list
        """

        res: list = []
        champs: list[QgsField] = layer.fields()  # list des champs de la couche
        # filtrer les champs dont le nom est identique au champ recherche (resultat longueur 1 ou 0)
        champsTrouves = list(filter(lambda x: x.name() == champRecherche, champs))

        if (len(champsTrouves) > 0):
            # obtenir les entitées sélectionnées
            features: list[QgsFeature] = layer.selectedFeatures()
            for feature in features:
                res.append(feature.attribute(champRecherche))

        return res
