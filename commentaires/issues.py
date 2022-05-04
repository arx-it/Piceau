import requests
from typing import List
from qgis.core import Qgis, QgsPoint, QgsPointXY, QgsGeometry
from qgis.gui import QgisInterface
from qgis.PyQt.QtWidgets import QDockWidget, QLineEdit, QPushButton
from qgis.PyQt.QtGui import QDoubleValidator
from qgis.PyQt.QtCore import Qt
from .connexion import Connexion
from ..pick_utilitaire import Pick_Tools
from qgis.gui import QgsMapToolEmitPoint, QgsMapCanvas
from ..outils_geometrie.outils_geometrie import OutilsGeometrie


class Issues():

    _mainWidget: QDockWidget
    _iface: QgisInterface
    _connexion: Connexion
    _formulaireVerrouille: bool
    _champs: List[dict]
    _config: dict
    _canvas: QgsMapCanvas
    _pointClickTool: QgsMapToolEmitPoint
    _checkMapTool: any

    def __init__(self, mainWidget: QDockWidget, iface: QgisInterface, connexion: Connexion):
        self._mainWidget = mainWidget
        self._iface = iface
        self._connexion = connexion
        self._formulaireVerrouille = True
        self._mainWidget.input_envoyer.clicked.connect(lambda: self.creeAnomalie(self))
        self._mainWidget.input_effacer.clicked.connect(lambda: self.viderFormulaire(self))
        self._config = Pick_Tools().lire_fichier_config()
        self.initValidationFormulaire()
        self._checkMapTool = None

        # Outil coordonnées
        self.initOutilCoordonneesClick()
        self._mainWidget.get_coord.clicked.connect(self.coordonneesClick)

    # --------------------------------------------------------------------
    # -- Gestion Formulaire-----------------------------------------------
    # --------------------------------------------------------------------
    def changeEtatFormulaire(self, connecte: bool):
        """
        Mise à jour de l'etat du formulaire. L'etat est à "verouille" lorsque l'utilisateur est deconnecte et inversement

        :params connecte: numero de bouton de souris clicke (1=gauche, 2=droite...)
        :type connecte: bool
        """
        self._formulaireVerrouille = not connecte
        if (self._formulaireVerrouille):
            self.arretSaisieCoordonnees()
        self.setEtatFormulaire()

    def setEtatFormulaire(self):
        """
        Active/Desactive le formulaire
        """
        # Active / Desactive les boutons
        # Etat du boutton envoye est defini selon le contenu du formulaire (--> utile si des champs sont deja saisis)
        if (self._formulaireVerrouille is False):
            self.validationInputs()
        else:
            self._mainWidget.input_envoyer.setDisabled(True)
        self._mainWidget.input_effacer.setDisabled(self._formulaireVerrouille)
        self._mainWidget.get_coord.setDisabled(self._formulaireVerrouille)

        # Active/ Desactive les champs
        for champ in self._config["anomalies"]["champs"]:
            if (champ["modifiable"] is True):
                lineEdit = getattr(self._mainWidget, champ["nom"])
                lineEdit.setDisabled(self._formulaireVerrouille)

    def viderFormulaire(self, checked=None):
        """
        Vide le contenu du formulaire
        """
        for champ in self._config["anomalies"]["champs"]:
            if (champ["modifiable"] is True):
                lineEdit = getattr(self._mainWidget, champ["nom"])
                lineEdit.clear()

    def initValidationFormulaire(self):
        """
        Connexion aux champs du formulaire pour verifier leur validite
        """
        for champ in self._config["anomalies"]["champs"]:
            lineEdit = getattr(self._mainWidget, champ["nom"])
            lineEdit.textChanged.connect(self.validationInputs)
            if ("type" in champ):
                if(champ["type"] == "double"):
                    validator = QDoubleValidator()  # validation chiffres reels
                    validator.Notation = QDoubleValidator().StandardNotation  # pas de notations scientifiques
                    lineEdit.setValidator(validator)  # accept seulement des reels

    def validationInputs(self):
        """
        Verifie que les champs du formulaire sont valides --> on check que les champs "requis" soient bien rempli par l'utilisateur
        """
        estValide = True

        for champ in self._config["anomalies"]["champs"]:
            lineEdit = getattr(self._mainWidget, champ["nom"])
            if ("requis" in champ):
                if(champ["requis"] is True and len(lineEdit.text()) == 0):
                    estValide = False

        if (estValide is True):
            self._mainWidget.input_envoyer.setDisabled(False)
        else:
            self._mainWidget.input_envoyer.setDisabled(True)

    # --------------------------------------------------------------------
    # -- Envoir du formulaire vers API -----------------------------------
    # --------------------------------------------------------------------
    def creeAnomalie(self, checked=None):
        """
        Creation et Envoi de la requete http à l'api Redmine(forge BRGM)
        pour la creation d'une anomalie
        """
        # Verrouille le bouton d'envoi pendant le traitement de la requete
        self._mainWidget.input_envoyer.setDisabled(True)

        url = self._config["api"]["forgeBrgm"]["url"] + "/issues.json"
        apiKey = self._connexion.getApikey()
        headers = {'X-Redmine-API-Key': apiKey}
        titre = self._mainWidget.input_titre.text()
        description = self._mainWidget.input_description.toPlainText()
        body = self.creationBody(titre, description)

        r = requests.post(url, headers=headers, json=body)
        if (r.status_code == 201):
            self._mainWidget.input_envoyer.setDisabled(False)  # deverouiller avec le retour
            self._iface.messageBar().pushSuccess("Anomalie enregistrée avec succès.", titre)
            self.viderFormulaire()
        else:
            self._mainWidget.input_envoyer.setDisabled(False)  # deverouiller avec le retour
            self._iface.messageBar().pushWarning("Echec de la creation de l'anomalie.", "Envoi impossible")

    def creationBody(self, titre: str, description: str) -> dict:
        """
        Creation du corps de la requete HTTP pour l'api Redmine
        """
        # renseigne les donnees pour les champs "normaux" (!= de custom fields)
        payload = {
            "issue": {
                "project_id": self._config["api"]["forgeBrgm"]["projectId"],
                "subject": titre,
                "description": description,
                "priority_id": self._config["api"]["forgeBrgm"]["defaulPriorityId"],
                "tracker_id": self._config["api"]["forgeBrgm"]["defaultTrackerId"],
                "status_id": self._config["api"]["forgeBrgm"]["defaulStatusId"],
            }
        }

        # creation de la cle "custom fields"
        payload["issue"]["custom_fields"] = []

        for champCustom in self._config["api"]["forgeBrgm"]["champs_custom"]:
            lineEdit = getattr(self._mainWidget, champCustom["nom_input"])
            if (len(lineEdit.text()) > 0):
                val = {"value": lineEdit.text(), "id": champCustom["id"]}
                payload["issue"]["custom_fields"].append(val)

        # on efface la cle "custom fields" si aucun de ces champs n'a ete saisi par l'utilisateur
        if (len(payload["issue"]["custom_fields"]) == 0):
            payload["issue"].pop('custom_fields', None)

        return payload

    # --------------------------------------------------------------------
    # -- Gestion du bouton coordonnees -----------------------------------
    # --------------------------------------------------------------------
    def initOutilCoordonneesClick(self):
        """
        Initialisation de l'outil pour obtenir les coordonnees
        """
        self._canvas = self._iface.mapCanvas()
        self._pointClickTool = QgsMapToolEmitPoint(self._canvas)  # init outil
        self._pointClickTool.canvasClicked.connect(self.obtenirCoordonnees)

    def coordonneesClick(self, Checked):
        """
        Demarrer l'outil d'obtention des coordonnees au clic
        """
        if(Checked):
            self.SuiviOutilSelectionne(True)  # On active l'observation du changement d'outil par l'utilisateur
            self._mainWidget.get_coord.setText("Arrêter la saisie")
            self._canvas.setMapTool(self._pointClickTool)
        else:
            self.arretSaisieCoordonnees()

    def obtenirCoordonnees(self, point: QgsPointXY, button: Qt.MouseButton):
        """
        Coordonnees obtenu au click de la souris
        :params point: Point retourné au click sur la carte
        :type point: QgsPointXY

        :params button: numero de bouton de souris clicke (1=gauche, 2=droite...)
        :type button: Qt.MouseButton
        """

        # Obtenir les coordonnees en WGS 84
        epsgWGS84 = 4326
        transformer = OutilsGeometrie.genererTransformer(epsgWGS84)
        geom = QgsGeometry(QgsPoint(point))
        geom.transform(transformer)

        lon = str(round(geom.asPoint().x(), 6))
        lat = str(round(geom.asPoint().y(), 6))
        # Afficher les coordonnees dans le formulaire
        self._mainWidget.input_lat.setText(lat)
        self._mainWidget.input_long.setText(lon)

    def ChangementOutilSelectionne(self, newTool, oldTool):
        """
        Desactive l'outil "Emit Point" si un autre outil a été selectionné
        :params newTool: nouvel outil selectionné
        :type newTool: any | None

        :params newTOldTooool: précédent outil selectionné
        :type OldToo: any | None
        """
        if(newTool != self._pointClickTool):
            self.arretSaisieCoordonnees()

    def arretSaisieCoordonnees(self):
        """
        Arreter la saisie de la coordonnée
        """
        self._mainWidget.get_coord.setText("Saisir un point sur la carte")
        self._mainWidget.get_coord.setChecked(False)
        self.SuiviOutilSelectionne(False)  # arrete d'observer les evenements lorsqu'un outil change
        if(self._canvas.mapTool() == self._pointClickTool):
            self._canvas.unsetMapTool(self._pointClickTool)

    def SuiviOutilSelectionne(self, activer: bool):
        """
        Active/Desactive le fait de regarder si l'outil de carte a été modifié.
        :params activer: nouvel outil selectionné
        :type activer: bool
        """
        if (activer is True):
            if (self._checkMapTool is None):
                # activation de l'outil pour surveiller l'outil de carte utilise
                self._checkMapTool = self._canvas.mapToolSet.connect(self.ChangementOutilSelectionne)
        else:  # use to prevent bug
            if (self._checkMapTool is not None):
                self._canvas.mapToolSet.disconnect()  # arrete d'observer les evenements lorsqu'un outil change
                self._checkMapTool = None
