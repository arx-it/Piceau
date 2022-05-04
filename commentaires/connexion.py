import os
import requests
from requests.auth import HTTPBasicAuth
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.PyQt.QtCore import QByteArray
from qgis.PyQt.QtGui import QMovie


class Connexion():

    _mainWidget: QDockWidget
    _parent: any
    _apiKey: str
    _loader: bool
    _utilisateurConnecte: str

    def __init__(self, mainWidget: QDockWidget, parent):
        self._mainWidget = mainWidget
        self._parent = parent
        self._apiKey = None
        self._utilisateurConnecte = None
        self._mainWidget.label_connecte.hide()

        self.setLoader()

        # configure bouton se connecter et se deconnecter
        self._mainWidget.btn_connecter.clicked.connect(lambda: self.seConnecter(self))

    def setLoader(self):

        script_dir = os.path.dirname(__file__)
        rel_path = "loader_min.gif"
        abs_path = os.path.join(script_dir, rel_path)

        # TODO  organize this area
        movie = QMovie(abs_path)
        movie.setCacheMode(QMovie.CacheAll)
        movie.setSpeed(100)

        self._loader = self._mainWidget.loader
        self._loader.setMovie(movie)
        self._loader.hide()
        movie.start()

    def getApikey(self) -> str:
        """
        Getter: retourne la cle d'api
        """
        return self._apiKey

    def seConnecter(self, checked=None):
        """
        Obtenir la clé d'api de l'utilisateur à la connexion ou
        la supprimer si c'est une deconnexion
        """

        if (self._apiKey):
            # cle apiKey initialise ==> deconnexion
            self._apiKey = None
            self.setEtatBouton()

        else:
            # cle apiKey initialise ==> connexion
            self._loader.show()
            identifiant = self._mainWidget.input_identifiant.text()
            motDePasse = self._mainWidget.input_password.text()
            url = "https://forge-scientifique.brgm-rec.fr/users/current.json"
            myAuth = HTTPBasicAuth(identifiant, motDePasse)
            r = requests.get(url, auth=myAuth)
            if (r.status_code == 200):
                res = r.json()
                self._apiKey = res["user"]["api_key"]
                self._utilisateurConnecte = identifiant
                self._loader.hide()
                # evenement -> connexion etablie
                self._parent._iface.messageBar().pushSuccess("Connexion à la forge BRGM.", "Connexion réussie")
                self.setEtatBouton()
            else:
                self._parent._iface.messageBar().pushWarning("Echec de connexion à la forge BRGM.", "Connexion impossible")
                self._loader.hide()

    def setEtatBouton(self):
        """
        Change l'etat des boutons et textbox du formulaires d'identification
        """
        if (self._apiKey):
            self._mainWidget.btn_connecter.setText("Se déconnecter")
            self._mainWidget.input_identifiant.setDisabled(True)
            self._mainWidget.input_identifiant.hide()
            self._mainWidget.input_password.setText("")  # vide le mot de passe par securite
            self._mainWidget.input_password.setDisabled(True)
            self._mainWidget.input_password.hide()
            self._parent.estConnecte(True)
            text = "Connecté en tant que " + self._utilisateurConnecte
            self._mainWidget.label_connecte.setText(text)
            self._mainWidget.label_connecte.show()
        else:
            self._mainWidget.label_connecte.hide()
            self._mainWidget.btn_connecter.setText("Se connecter")
            self._mainWidget.input_identifiant.setDisabled(False)
            self._mainWidget.input_identifiant.show()
            self._mainWidget.input_password.setDisabled(False)
            self._mainWidget.input_password.show()
            self._parent.estConnecte(False)
