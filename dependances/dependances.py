import subprocess
import importlib
import os
import sys

from qgis.PyQt.QtWidgets import QMessageBox
from ..pick_utilitaire import Pick_IO


class Dependances:

    autorisation_installation_extensions = None

    # installation des dépendances
    @staticmethod
    def installation_dependances(dependance: str):
        # on regarde si la dependance est chargee
        loader = importlib.find_loader(dependance)
        result: bool = loader is not None

        # Installation de la dependances si manquante
        if result is False:
            # Verification consentement de l'utilisateur -> On lui pose la question une seule fois
            if Dependances.autorisation_installation_extensions is None:
                Dependances.demande_installation_dependances()

            # si autorisation, installation des extensions
            if Dependances.autorisation_installation_extensions is True:
                subprocess.call(['python3', '-m', 'pip', 'install', dependance, '--user'])

    # Demande d'autorisation pour l'installation de dépendances
    @staticmethod
    def demande_installation_dependances():
        msgBox: QMessageBox = QMessageBox()
        msgBox.setWindowTitle("Pickeau")
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("PickEau : bibliothèques Python manquantes")
        informative_text = """
Des bibliothèques Python nécessaires au fonctionnement de l'extension PickEau sont manquantes.
Qgis peut les installer automatiquement. Si vous répondez non ou si l'installation échoue, consultez la documentation de PickEau pour les installer manuellement ou contactez votre administrateur.\n
Voulez-vous installer automatiquement les bibliothèques manquantes ?
                """
        msgBox.setInformativeText(informative_text)
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.No)
        msgBox.buttonClicked.connect(Dependances.reponse)
        msgBox.exec()

    @staticmethod
    def reponse(i):
        reponse = i.text()
        if reponse == "OK":
            Dependances.autorisation_installation_extensions = True
        else:
            Dependances.autorisation_installation_extensions = False


# chemin du fichier requirements et lecture
script_dir = os.path.dirname(__file__)
rel_path = 'requirements.txt'
abs_path = os.path.join(script_dir, rel_path)

contenu_fichiers = Pick_IO.lire_fichier_text(abs_path)
dependances: [str] = contenu_fichiers.splitlines()


for dependance in dependances:
    Dependances.installation_dependances(dependance)
