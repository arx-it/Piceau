
"""
    3 Etats à déterminer pour l'extension plotly:
        1. L'extension est-elle installée ?
        2. L'extension est-elle chargée ?
        3. L'extension est-elle démarrée ?
"""
import sys
import os
from typing import List, Dict
from qgis.core import QgsApplication
from qgis.utils import plugins, available_plugins, isPluginLoaded, startPlugin, unloadPlugin, plugins_metadata_parser
from qgis.PyQt.QtWidgets import QMessageBox
from ..pick_utilitaire import Pick_IO


class Qgis_Extensions:

    plugin_dir: str
    dependances: List[dict]

    def __init__(self, plugin_dir: str):
        """Constructor.
        :param plugin_dir: chemin de la racine du plugin.
        :type plugin_dir: string
        """
        # lecture config
        self.plugin_dir = plugin_dir
        self.utilitaire = Pick_IO()
        rel_path = 'configs/default_config.json'
        abs_path_config = os.path.join(plugin_dir, rel_path)
        self.config: dict = self.utilitaire.lire_fichier_json(abs_path_config)

    def demarrer_extensions(self) -> dict:
        """
        Verifie que les plugins Qgis soient installées dans la version demandée, puis
        démarre les plugins.

        :returns: contient l'etat des plugins (demarree et dans la version exigee).
        :rtype: dict
        """

        res = {}  # init var
        dependances = self.config["dependances"]
        for dependance in dependances:
            res[dependance["nom"]] = {}
            res[dependance["nom"]]["est_installee"] = False
            est_installe = self.verification_extension_installee_demarrage(dependance["nom"])

            # check installee
            if est_installe is True:
                res[dependance["nom"]]["est_installee"] = True

                # check version
                res[dependance["nom"]]["version_correct"] = False
                res[dependance["nom"]]["version_correct"] = self.verification_version(dependance["nom"], dependance["version"])

                # demarrer extension
                res[dependance["nom"]]["est_demarree"] = False
                if (res[dependance["nom"]]["version_correct"] is True):
                    self.demarrer_extension(dependance["nom"])
                    res[dependance["nom"]]["est_demarree"] = True

        return res

    def demarrer_extension(self, nom_extension: str) -> bool:
        """
        Demarre une extension qgis si elle est chargee

        :param nom_extension: nom de l'extension
        :type nom_extension: string

        :returns: renvoi vrai si l'extension est charge et qu'elle a été lancé (et inversement)
        :rtype: bool
        """
        est_chargee = self.charger_extension(nom_extension)

        if (est_chargee is False):
            # puis on demarre le plugin
            plugins[nom_extension].run()
            return True
        else:
            return False

    # Verifier qu'une extension est installe
    def verification_extension_installee(self, nom_extension: str):
        """
        Demarre une extension qgis si elle est chargee
        :param nom_extension: nom d'une extension Qgis
        :type nom_extension: string

        :returns: renvoi vrai si l'extension est installee
        :rtype: bool
        """
        plugins_installees: [str] = available_plugins
        if nom_extension in plugins_installees:
            return True
        else:
            return False

    # Verifier qu'une extension est installee
    def verification_extension_installee_demarrage(self, nom_extension: str) -> bool:
        """
        Verifie qu'une extension qgis est installee. Si elle ne l'est pas, un avertissement apparait au demarrage

        :param nom_extension: nom de l'extension
        :type nom_extension: string
        
        :return: renvoi vrai si l'extension est installée (et inversement)
        :rtype: bool
        """

        est_installee = self.verification_extension_installee(nom_extension)
        if est_installee is False:
            self.affichage_message_installee(nom_extension)

        return est_installee

    def charger_extension(self, nom_extension: str) -> bool:
        """
        Verifie qu'une extension qgis est chargee

        :param nom_extension: nom de l'extension
        :type nom_extension: string

        :return: renvoi vrai si l'extension est chargee (et inversement)
        :rtype: bool
        """
        # on charge l'extension si elle n'est pas charge
        plugin_charge = isPluginLoaded(nom_extension)
        if (plugin_charge is False):
            startPlugin(nom_extension)
            return True
        else:
            return False

    # Message si extension n'est pas installee
    def affichage_message_installee(self, nom_extension: str):
        """
        Affichage un message d'avertissement si une extension n'est pas installee

        :param nom_extension: nom de l'extension
        :type nom_extension: string
        """

        message = "L'extension " + nom_extension + " n'est pas installée, certaines fonctionnalités pourraient ne pas fonctionner.\n\n"

        if nom_extension == "DataPlotly":
            script_dir = os.path.dirname(__file__)
            rel_path = 'message.txt'
            abs_path = os.path.join(script_dir, rel_path)

            contenu = Pick_IO.lire_fichier_text(abs_path)
            message = message + contenu

        QMessageBox.warning(None, nom_extension + " : extension Qgis non installée", message)

    # Message si extension n'est pas installee
    def affichage_message_version(self, version_installee: str, version_exigee: str, nom_extension: str):
        """
        Affichage un message d'avertissement si une extension est installee dans une mauvaise version

        :param nom_extension: nom de l'extension
        :type nom_extension: string

        :param version_installee: version installee de l'extension
        :type version_installee: string

        :param version_exigee: version exigee de l'extension
        :type version_exigee: string
        """
        message = "La version de l'extension " + nom_extension + " n'est pas compatible avec votre version de Pickeau, certaines fonctionnalités pourraient ne pas fonctionner.\n\n"
        message_complementaire = "version attendue: '" + version_exigee + "', version installée: '" + version_installee + "'"
        message_complet = message + message_complementaire

        title = nom_extension + " : extension Qgis non installée"

        self.affichage_message(title, message_complet)

    # Message si extension n'est pas installee
    def affichage_message(self, title: str, message: str):
        QMessageBox.warning(None, title, message)

    def verification_version(self, nom_extension: str, version_exigee: str) -> bool:
        """
        Verifie la version installee d'une extensions

        :param nom_extension: nom de l'extension
        :type nom_extension: string

        :param version_installee: version installee de l'extension
        :type version_installee: string

        :param version_exigee: version exigee de l'extension
        :type version_exigee: string

        :return: renvoi vrai si l'extension est chargee (et inversement)
        :rtype: bool
        """

        # TODO documentation + verification version et message d erreur
        metadata = plugins_metadata_parser[nom_extension]
        version_installee = metadata['general']['version']
        if (version_installee == version_exigee):
            return True
        else:
            self.affichage_message_version(version_installee, version_exigee, nom_extension)
            return False
