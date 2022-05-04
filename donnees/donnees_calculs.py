
import requests
from urllib.parse import quote
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.PyQt.QtCore import QDate
from qgis.gui import QgisInterface
from qgis.core import QgsFeature, QgsProject, QgsLayerTreeGroup
from ..pick_utilitaire import Pick_Tools
from .layers_stations import StationsLayers
from .traitement_resultats_api import ResultatsApi
from ..utilitaires.utilitaire_couches import UtilitaireCouches


class DonneesCalculs():

    _mainWidget: QDockWidget
    _iface: QgisInterface
    _config: dict
    _stationsLayers: StationsLayers
    _resultatsApi: ResultatsApi

    def __init__(self, mainWidget: QDockWidget, iface: QgisInterface):
        self._mainWidget = mainWidget
        self._config = Pick_Tools().lire_fichier_config()
        self._iface = iface
        self._mainWidget.btn_dl_stats_piezo.clicked.connect(lambda: self.dlDatas(self))
        self._stationsLayers = StationsLayers(mainWidget, self._iface)
        self._resultatsApi = ResultatsApi(mainWidget, self._iface)

    def dlDatas(self, checked=None):
        baseUrl = self._config["api"]["piceau"]["url"] + "/" + self._config["api"]["piceau"]["routes"]["stats_descriptives_piezo"]

        # obtenir couche piezo selectionnee
        couche_piezos = self._stationsLayers.activeLayerEstCouchePiezometre()
        groupe_actif: QgsLayerTreeGroup = self._iface.layerTreeView().currentGroupNode()

        if (couche_piezos):
            piezos = self.getStationsPiezoSelectionnees(couche_piezos)
            if (piezos):
                url = baseUrl + "/" + piezos + "/" + self.getDateDebut() + "/" + self.getDateFin()
                res = requests.get(url)
                if (res.status_code == 200):
                    # resultat
                    resultat = res.json().keys()

                    if(len(resultat) > 0):
                        dossier = self._resultatsApi.statsDescriptivesPiezo(res.json(), couche_piezos, res)

                        # Ouvrir les couches du layer (cf fonction utilitaire lire dpkg)
                        newGroup = groupe_actif.addGroup(dossier["nomDossierCree"])
                        UtilitaireCouches.lire_toutes_couches_geopackage(dossier["nom_fichier_dpkg"], newGroup, True)

                    else:
                        self._iface.messageBar().pushWarning("le téléchargement des données n'a retourné aucune donnée", "Aucun résultat")
                else:
                    self._iface.messageBar().pushWarning("le téléchargement des données à échoué", "Echec du téléchargement")
        else:
            self._iface.messageBar().pushWarning("Sélectionner une couche Station_Piézomètres", "Echec du téléchargement")

    def getDateDebut(self) -> str:
        date: QDate = self._mainWidget.stats_dateDebut.date()
        return date.toString("yyyy-MM-dd")

    def getDateFin(self) -> str:
        date: QDate = self._mainWidget.stats_dateFin.date()
        return date.toString("yyyy-MM-dd")

    def getStationsPiezoSelectionnees(self, couche_piezos):
        listCodesBss = self._stationsLayers.getBssStations(couche_piezos, "code_bss")
        listCodesFormated = self.formatCodeBss(listCodesBss)
        return listCodesFormated

    def formatCodeBss(self, listCodesBss: list) -> str:
        if (len(listCodesBss) > 0):
            codesBssFormatted = "["
            for listCodeBss in listCodesBss:
                codeBssFormatted = quote(listCodeBss, safe='')
                virguleEncoded = quote(",", safe='')
                codesBssFormatted += codeBssFormatted + virguleEncoded
            codesBssFormatted = codesBssFormatted[:-3]  # suppression derniere virgule encoded (3 caracteres %2C)
            codesBssFormatted += "]"
            return codesBssFormatted
        else:
            self._iface.messageBar().pushWarning("Sélectionner au moins une station de la couche Station_Piézomètres", "Echec du téléchargement")
