import json
import pandas as pd
import numpy as np
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.core import QgsMapLayer, QgsVectorLayer, QgsField, QgsFeature, QgsProject, QgsLayerTreeGroup
from qgis.gui import QgisInterface
from .donnees_api import DonneeApi
from ..utilitaires.utilitaire_couches import UtilitaireCouches


class ResultatsApi():

    _mainWidget: QDockWidget
    _iface: QgisInterface

    def __init__(self, mainWidget: QDockWidget, iface: QgisInterface):
        self._mainWidget = mainWidget
        self._iface = iface

    def statsDescriptivesPiezo(self, res: dict, couche_piezos: QgsMapLayer, res2: any) -> QgsVectorLayer:
        """
        Traitement du résultat de la requete couche descriptive

        :param res: Resultat json de la requete
        :type res: dict

        :param couche_piezos: couche piezos contenant les stations ayant servi à la requete stats descriptive
        :type couche_piezos: dict
        """
        # traitement des résultats
        donneesApi = self.formatageResultats(res)

        # Creation dossier geopackage
        chemin_dossier_geopackage_origine = UtilitaireCouches.get_chemin_dossier_geopackage_depuis_couche(couche_piezos)
        dossier = UtilitaireCouches.creation_dossier_geopackage(chemin_dossier_geopackage_origine, "stats_descriptive")
        nom_fichier = dossier["nomDossierCree"] + ".gpkg"
        dossier["nom_fichier_dpkg"] = dossier["cheminDossierCree"] + "/" + nom_fichier

        ajout_a_fichier_existant = False
        for donneeApi in donneesApi:
            table = donneeApi.creationTable()
            UtilitaireCouches.ecrire_couche_geopackage(dossier["cheminDossierCree"], table, donneeApi._nomTable, nom_fichier, "", "", ajout_a_fichier_existant)
            ajout_a_fichier_existant = True  # on ne créé le fichier que pour la première valeur

        return dossier

    def creationChamp(self, nomChamp: str, valeur: any) -> QgsField:
        """
        Création d'un champ QGis à partir d'une valeur

        :param nomChamp: Nom du champ
        :type nomChamp: string

        :param valeur: valeur de référence pour établir le type de champ à créer
        :type valeur: any

        :return: Champ
        :rtype: QgsField
        """
        if (type(valeur) is str):
            varType = QVariant.String
            champ = QgsField(nomChamp, varType)
        else:
            varType = QVariant.Double
            champ = QgsField(nomChamp, varType)

        return champ

    def formatageResultats(self, res: dict):
        """
        Mise en forme des données json retourné par l'API Piceau

        :param res: réponse des l'api piceau
        :rtype: dict

        :return: données mise en forme pour être mise en tableau
        :rtype: dict
        """
        donnees = {
            "donneesStations": {
                "champs": [],
                "valeurs": []
            }
        }

        donneesNouvelleTable = ""

        # reponse de l'api transformée en tableau
        jsonRes = json.dumps(res)
        df = pd.read_json(jsonRes)
        dft = df.T
        liste_colonnes = dft.columns
        index = dft.index
        liste_index = index.to_numpy()

        nouvelleTables = []

        # creation de la liste des champs
        for colonne in liste_colonnes:

            value = dft.at[dft.iloc[0]['bss_id'], colonne]
            if(type(value) is not list):
                champ = self.creationChamp(colonne, value)
                donnees["donneesStations"]["champs"].append(champ)
            else:
                nouvelleTables.append(colonne)

        # creation des donnes stations
        for index in liste_index:
            ligne_donnees = []

            for colonne in liste_colonnes:
                value = dft.at[index, colonne]
                if(type(value) is not dict):
                    ligne_donnees.append(value)

            donnees["donneesStations"]["valeurs"].append(ligne_donnees)

        # creation des nouvelles tables
        donneesApi = []
        donneeApi = DonneeApi(donnees["donneesStations"]["champs"], donnees["donneesStations"]["valeurs"], "stations")
        donneesApi.append(donneeApi)

        data = {}
        for nouvelleTable in nouvelleTables:
            dataframes = []
            if (nouvelleTable == "stat_pz_chronique"):
                for bss_id in liste_index:
                    dataPerBss = pd.DataFrame(dft.at[bss_id, nouvelleTable])
                    # Convert index as column
                    dataPerBss.insert(0, 'bss_id', bss_id)
                    dataframes.append(dataPerBss)

            if (nouvelleTable == "chronique_stat_pz_pas_mensuel" or nouvelleTable == 'stat_pz_par_annee' or nouvelleTable == 'stat_pz_par_mois'):
                dataframes = []
                for bss_id in liste_index:
                    dataPerBssPerMonth = pd.DataFrame(dft.at[bss_id, nouvelleTable][0])
                    dataPerBssPerMonthT = dataPerBssPerMonth.T
                    # Convert index as column
                    dataPerBssPerMonthT = dataPerBssPerMonthT.reset_index().rename(columns={'index': 'date'})
                    # insert bss id
                    dataPerBssPerMonthT.insert(0, 'bss_id', bss_id)
                    dataframes.append(dataPerBssPerMonthT)

            data[nouvelleTable] = pd.concat(dataframes, ignore_index=True)
            donnees_pr_creation_table = self.prepareTableForQgis(data[nouvelleTable])
            donneeApiNouvelleTable = DonneeApi(donnees_pr_creation_table["champs"], donnees_pr_creation_table["valeurs"], nouvelleTable)
            donneesApi.append(donneeApiNouvelleTable)
        return donneesApi

    def prepareTableForQgis(self, df):
        """
        Preparation d'un dataframe pour etre converti en table QGis

        :param df: dataframe panda contenant la table a convertir en Qgis
        :rtype: pandas.DataFrame

        :return: donnees preparer pour etre mise en Table sous Qgis (un dict  champs [List de QGis Field] et valeurs [List de valeurs])
        :rtype: dict
        """
        donnees = {
            "champs": [],
            "valeurs": []
        }

        # obtenir les champs
        liste_colonne = df.columns
        for colonne in liste_colonne:
            value = df.at[df.index[0], colonne]
            if (isinstance(value, np.float64)):
                value = np.float64(value).item()
            if (isinstance(value, np.int64)):
                value = np.int64(value).item()
            if(type(value) is not dict):
                champ = self.creationChamp(colonne, value)
                donnees["champs"].append(champ)

        # obtenir les valeurs
        indexs = df.index
        liste_index = indexs.to_numpy()

        for index in liste_index:
            ligne_donnees = []
            for colonne in liste_colonne:
                value = df.at[index, colonne]
                if (isinstance(value, np.float64)):
                    value = np.float64(value).item()
                if (isinstance(value, np.int64)):
                    value = np.int64(value).item()
                if(type(value) is not dict):
                    ligne_donnees.append(value)

            donnees["valeurs"].append(ligne_donnees)
        return donnees
