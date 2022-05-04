# -*- coding: utf-8 -*-
"""
@author: Laurent Vaute
email: l.vaute@brgm.fr
copyright: (C) 2019 by BRGM

Module PickEau contenant une classe pick_requete permettant :
    - de définir les adresses ip des serveurs hubeau, sandre et ades
    - d'envoyer des requêtes sur ces 3 serveurs
    - de mettre à jour les lexiques PickEau dérivés des listes nationales des paramètres [et des masses d'eau (inutilisé)]
"""

import requests
import pandas as pd
from io import StringIO
import os
import xmltodict
import gzip
import json
import csv

class Pick_Req():
    """
    Classe Pick_Req permettant :
        - de définir les adresses ip des serveurs hubeau, sandre et ades
        - d'envoyer des requêtes sur ces 3 serveurs
        - de mettre à jour les lexiques PickEau dérivés des listes nationales des paramètres [et des masses d'eau (inutilisé)]
    Cette classe prend en paramètres deux instances des classes Pick_IO et Pick_Tools du module pick_utilitaire :
        - Pick_IO : fonctions de lecture / écriture de fichiers externes
        - Pick_Tools : fonctions utilitaires diverses
    """
    def __init__(self, pio, ptools):

        self.pio = pio
        self.ptools = ptools

        # Définition des chemins du fichier des adresses ip et des fichiers des listes nationales
        self.dossier_plugin = self.ptools.trouver_dossier_module()
        chem_adresses_ip = os.path.join(self.dossier_plugin, 'pick_adresses_ip.json')
        # chem_ln_masses_eau = os.path.join(self.dossier_plugin, 'pick_ln_masses_eau.csv')
        chem_ln_parametres = os.path.join(self.dossier_plugin, 'pick_ln_parametres.csv')

        # Lecture de fichiers externes : fichier des adresses ip
        dict_adresses_ip = self.pio.lire_fichier_json(chem_adresses_ip)

        # Définition des adresses ip des serveurs pour construire les différentes requêtes hubeau, sandre et ades
        self.ip_hubeau_niveaux_nappes_stations_csv = dict_adresses_ip['ip_hubeau']['niveaux_nappes_stations_csv']
        self.ip_hubeau_qualite_nappes_stations_csv = dict_adresses_ip['ip_hubeau']['qualite_nappes_stations_csv']
        self.ip_hubeau_niveaux_nappes_chroniques_csv = dict_adresses_ip['ip_hubeau']['niveaux_nappes_chroniques_csv']
        self.ip_hubeau_qualite_nappes_analyses_csv = dict_adresses_ip['ip_hubeau']['qualite_nappes_analyses_csv']
        self.ip_sandre_parametres_csv_gz = dict_adresses_ip['ip_sandre']['parametres_csv_gz']
        self.ip_sandre_groupes_csv_gz = dict_adresses_ip['ip_sandre']['groupes_csv_gz']
        # self.ip_sandre_masses_eau_csv_gz = dict_adresses_ip['ip_sandre']['masses_eau_csv_gz']
        self.ip_ades_unites_parametres_support_liquide_xml = dict_adresses_ip['ip_ades']['unites_parametres_support_liquide_xml']
        self.ip_ades_parametres_xml = dict_adresses_ip['ip_ades']['parametres_xml']

        # Définition des listes de champs renvoyés par les requêtes et permettant de construire les df résultats
        self.list_col_metadata_niveaux_nappes_chroniques_csv = dict_adresses_ip["list_col_metadata_niveaux_nappes_chroniques_csv"]
        self.list_col_data_niveaux_nappes_chroniques_csv = dict_adresses_ip["list_col_data_niveaux_nappes_chroniques_csv"]
        self.list_col_metadata_qualite_nappes_analyses_csv = dict_adresses_ip["list_col_metadata_qualite_nappes_analyses_csv"]
        self.list_col_data_qualite_nappes_analyses_csv = dict_adresses_ip["list_col_data_qualite_nappes_analyses_csv"]

        # Définition des listes de champs demandés et passés aux requetes
        self.list_col_niveaux_nappes_chroniques_csv = self.list_col_metadata_niveaux_nappes_chroniques_csv + self.list_col_data_niveaux_nappes_chroniques_csv
        self.list_col_qualite_nappes_analyses_csv = self.list_col_metadata_qualite_nappes_analyses_csv + self.list_col_data_qualite_nappes_analyses_csv


    def requete_hubeau_par_dept(self, nom_administratif, list_dept, type_requete):
        """
        Envoie une requête sur le serveur Hubeau et renvoie un tuple contenant le dataframe et le statut de la requête
        :param nom_administratif:    nom de la zone administrative concernée par la requête
        :param list_dept:  liste de départements associée à la zone administrative
        :param type_requete:    type de requête possible :
                                "stations_qualite_csv"
                                "stations_piezo_csv"
                                "points_eau" (à venir en 2019)
        :return: tuple = ( dataframe des données reçues (DataFrame), statut de la requête (int | "type de requête inconnu") )
        """
        # Création de réponses par défaut pour la fonction
        df_data = pd.DataFrame()
        statut_requete = "type de requête inconnu"

        # Construction de la str de numéros de départements acceptée par hubeau
        str_point = '%2C'.join(list_dept)
        # Définition de la requête selon le type de requête passée en paramètre de la fonction
        if type_requete == "stations_qualite_csv":
            requete = self.ip_hubeau_qualite_nappes_stations_csv + "&num_departement=" + str_point
        elif type_requete == "stations_piezo_csv":
            requete = (self.ip_hubeau_niveaux_nappes_stations_csv)  # On ne tient pas compte du dept car hubeau ne le gère pas
        elif type_requete == "point_eau":   # à venir en 2019
            requete = ''
        else:
            requete = ''

        if requete != '':
            # Envoi de la requête au serveur ADES et réception de la réponse
            reponse = requests.get(requete)
            statut_requete = reponse.status_code

            # En cas de retour correct de la requête
            if statut_requete == 200:

                # Création d'un fileobject (représentation en mémoire d'un fichier)
                csv_fileobject = StringIO(reponse.text)
                # Teste si la réponse est non vide
                if csv_fileobject.seek(0, os.SEEK_END) > 0:
                    # Remet le pointeur du fichier au début du fichier texte
                    csv_fileobject.seek(0)
                    # Lecture par pandas du fichier texte dans un df
                    df_requete = pd.read_csv(csv_fileobject, sep=';')
                    # Ajout au df de champs d'information sur le retour de la requête Hubeau
                    df_requete['req_administratif'] = nom_administratif
                    df_requete['req_nb_points_recus'] = len(df_requete)
                    df_requete['req_statut'] = statut_requete
                    # Ajout du df au df total
                    if len(df_data) == 0:
                        df_data = df_requete
                    else:
                        df_data = df_data.append(df_requete)

        # Retour de la fonction
        return (df_data, statut_requete)


    def requete_hubeau_par_point(self, code_point, list_code_groupe, list_code_parametre, type_requete):
        """
        Envoie une requête sur le serveur Hubeau et renvoie un tuple contenant le dataframe et le statut de la requête
        NB : pour la qualité, il faut passer en paramètre soit une liste de groupes et une liste vide de paramètres,
        soit une liste de paramètres et une liste vide de groupes, sinon des paramètres seront manquants car
        la requête Hubeau considère l'intersection des groupes ET des paramètres.
        :param code_point:  code du point demandé (code_bss dans la version actuelle de Hubeau car seul code à être
                            accepté par les deux API eau souterraine
        :param list_groupe_parametre:  liste des codes SANDRE des groupes de paramètres concernés par la requête
        :param list_code_parametre:  liste des codes SANDRE des paramètres concernés par la requête
        :param type_requete:    type de requête possible :
                                "analyses_qualite_csv"
                                "chroniques_piezo_csv"
        :return: tuple = ( dataframe des données reçues (DataFrame), statut de la requête (int | "type de requête inconnu") )
        """
        # Création de réponses par défaut pour la fonction
        df_data = pd.DataFrame()
        statut_requete = "type de requête inconnu"

        # Construction des str de codes groupe, paramètres sandre et champs demandés acceptées par hubeau
        str_code_groupe = '%2C'.join(list_code_groupe)
        str_code_parametre = '%2C'.join(list_code_parametre)
        str_col_piezo = '%2C'.join(self.list_col_niveaux_nappes_chroniques_csv)
        str_col_qualite = '%2C'.join(self.list_col_qualite_nappes_analyses_csv)
        # Définition de la requête selon le type de requête passée en paramètre de la fonction
        if (type_requete == "analyses_qualite_csv") and (len(list_code_parametre) > 0):
            requete = (self.ip_hubeau_qualite_nappes_analyses_csv +
                       "&bss_id=" + code_point +
                       "&code_param=" + str_code_parametre +
                       "&fields=" + str_col_qualite)  # bss_id accepte aussi le code bss !
        elif (type_requete == "analyses_qualite_csv") and (len(list_code_groupe) > 0):
            requete = (self.ip_hubeau_qualite_nappes_analyses_csv +
                       "&bss_id=" + code_point +
                       "&code_groupe_parametre=" + str_code_groupe +
                       "&fields=" + str_col_qualite)  # bss_id accepte aussi le code bss !
        elif type_requete == "chroniques_piezo_csv":
            requete = (self.ip_hubeau_niveaux_nappes_chroniques_csv +
                       "&code_bss=" + code_point +
                       "&fields=" + str_col_piezo)  # On ne tient pas compte du paramètre car hubeau ne le gère pas
        else:
            requete = ''

        if requete != '':
            # Envoi de la requête au serveur ADES et réception de la réponse
            reponse = requests.get(requete)
            statut_requete = reponse.status_code

            # En cas de retour correct de la requête
            if statut_requete == 200:

                # Création d'un fileobject (représentation en mémoire d'un fichier)
                csv_fileobject = StringIO(reponse.text)
                # Teste si la réponse est non vide
                if csv_fileobject.seek(0, os.SEEK_END) > 0:
                    # Remet le pointeur du fichier au début du fichier texte
                    csv_fileobject.seek(0)
                    # Lecture par pandas du fichier texte dans un df
                    df_requete = pd.read_csv(csv_fileobject, sep=';')
                    # Ajout au df de champs d'information sur le retour de la requête Hubeau
                    df_requete['req_code_param'] = code_point
                    df_requete['req_nb_data_recues'] = len(df_requete)
                    df_requete['req_statut'] = statut_requete
                    # Ajout du df au df total
                    if len(df_data) == 0:
                        df_data = df_requete
                    else:
                        df_data = df_data.append(df_requete)

        # Retour de la fonction
        return (df_data, statut_requete)

    def requete_sandre(self, type_requete):
        """
        Envoie une requête sur le site du SANDRE
        Pour la construction des requêtes consulter le site :
        http: // www.sandre.eaufrance.fr / api - referentiel
        :param type_requete: type de la requête envoyée
        :return: tuple (dataframe, statut de la requête (int | type de requête inconnu))
        """
        # Création de réponses par défaut pour la fonction
        df_data = pd.DataFrame()
        statut_requete = "type de requête inconnu"

        # Définition de la requête
        if type_requete == "parametres_csv":
            requete = self.ip_sandre_parametres_csv_gz
        elif type_requete == "groupes_csv":
            requete = self.ip_sandre_groupes_csv_gz
        # elif type_requete == "masses_eau":
        #     requete = self.ip_sandre_masses_eau_csv_gz
        else:
            requete = ""

        if requete != "":
            # Envoi de la requête au serveur ADES et réception de la réponse
            reponse = requests.get(requete, stream=True)
            statut_requete = reponse.status_code

            # Contrôle du retour correct de la requête
            if statut_requete == 200:
                # Dézippage de la réponse (fileobject)
                zip_file = gzip.GzipFile(fileobj=reponse.raw)
                # Lecture du fileobject par pandas
                df_data = pd.read_csv(zip_file, sep=';')

        # Retour de la fonction
        return (df_data, statut_requete)


    def requete_ades(self, type_requete):
        """
        Envoie une requête sur le site ADES
        Pour la construction des requêtes consulter le code VBA du fichier Saisie_Analyses d'Ades:
        :param type_requete: type de la requête envoyée
        :return: tuple (dataframe, statut de la requête (int | type de requête inconnu))
        """
        # Création de réponses par défaut pour la fonction
        df_data = pd.DataFrame()
        statut_requete = "type de requête inconnu"

        # Définition de la requête
        if type_requete == "unites_parametres_support_liquide":
            requete = self.ip_ades_unites_parametres_support_liquide_xml
        elif type_requete == "parametres":
            requete = self.ip_ades_parametres_xml
        else:
            requete = ""

        if requete != "":
            # Envoi de la requête au serveur ADES et réception de la réponse
            reponse = requests.get(requete)
            statut_requete = reponse.status_code

            # Contrôle du retour correct de la requête
            if statut_requete == 200:

                # Extraction de la string constituant le résultat de la requête
                req_xml = reponse.text
                # Lecture de la string xml et conversion en dict
                dict_xml = xmltodict.parse(req_xml)  # , encoding='utf-8'
                # Lecture du dictionnaire par pandas en excluant les deux premiers niveaux de balise inutiles et vides
                if type_requete == "unites_parametres_support_liquide":
                    df_data = pd.DataFrame.from_dict(dict_xml['SERVICE_UNITSPARAM_SUPPORT_L']['UNITSPARAMSUPPORTL'])
                elif type_requete == "parametres":
                    df_data = pd.DataFrame.from_dict(dict_xml['SERVICE_PARAM']['PARAMETRE'])

        # Retour de la fonction
        return (df_data, statut_requete)


    # def maj_ln_masses_eau(self, chem_ln_masses_eau):
    #     """
    #     Réécrit la liste nationale des masses d'eau du Sandre.
    #     :param chem_ln_masses_eau: chemin du fichier csv à réécrire
    #     :return: None
    #     """
    #     # Création d'un df vide
    #     df_ln_masses_eau = pd.DataFrame()
    #
    #     # Obtention du csv des masses d'eau du SANDRE par requête sur webservice
    #     df_masses_eau, statut_requete_masses_eau = self.requete_sandre("masses_eau")
    #
    #     # Si la requete renvoie une réponse correcte --> on continue
    #     if statut_requete_masses_eau == 200:
    #         # Elimination de la deuxième ligne du df des masses d'eau
    #         df_masses_eau = df_masses_eau.drop(df_masses_eau.index[0])
    #         # On ne garde que les colonnes utiles
    #         df_masses_eau = df_masses_eau.loc[:,
    #             ['CdMasseDEau', 'CdEuMasseDEau', 'NomMasseDEau', 'StMasseDEau', 'CdCategorieMasseDEau', 'DateCreationMasseDEau', 'DateMajMasseDEau']]
    #         # Tri des lignes du df des paramètres
    #         df_masses_eau = df_masses_eau.sort_values('CdMasseDEau')
    #         # Elimination des masses d'eau gelées
    #         df_masses_eau = df_masses_eau[df_masses_eau['StMasseDEau'] != 'Gelé']
    #
    #     # Si le df n'est pas vide
    #     if len(df_masses_eau) != 0:
    #         df_ln_masses_eau = df_masses_eau
    #         # Ecriture du csv (écrase le fichier déjà présent)
    #         df_ln_masses_eau.to_csv(chem_ln_masses_eau, header=True, index=False, encoding='utf-8', sep=';')


    def maj_ln_parametres(self, chem_ln_parametre, chem_ln_groupe_parametre, chem_ln_groupe_code):
        """
        Réécrit 2 fichiers dérivés des listes nationales du Sandre (paramètres et groupes de paramètres)
        et d'Ades (paramètres présents dans Ades et unités de référence Ades) :
            - le fichier csv des paramètres présents dans ADES et de leurs groupes associés
              (potentiellement plusieurs groupes pour un même paramètre)
            - le fichier json des groupes de paramètres et de leur liste de codes paramètres associée
              (une seule liste de codes Sandre pour un même groupe)
        :param chem_ln_parametre: chemin du fichier csv à mettre à jour
        :return: None
        """
        # Création d'un df vide
        df_ln_parametres = pd.DataFrame()

        # Obtention du csv des paramètres du SANDRE par requête sur webservice
        df_param, statut_requete_parametres = self.requete_sandre("parametres_csv")

        # Obtention du csv des groupes de paramètres du SANDRE par requête sur webservice
        df_groupes, statut_requete_groupes = self.requete_sandre("groupes_csv")

        # Obtention du xml des unités des paramètres d'ADES par requête sur webservice
        df_unites_ades, statut_requete_unites_ades = self.requete_ades("unites_parametres_support_liquide")

        # Obtention du xml des paramètres d'ADES par requête sur webservice
        df_param_ades, statut_requete_parametres_ades = self.requete_ades("parametres")

        # Si toutes les requetes renvoient une réponse correcte --> on continue
        if (statut_requete_parametres == 200
                and statut_requete_groupes == 200
                and statut_requete_unites_ades == 200
                and statut_requete_parametres_ades == 200):

            # Elimination de la deuxième ligne du df des parametres
            df_param = df_param.drop(df_param.index[0])
            # On ne garde que les colonnes utiles
            df_param = df_param.loc[:,
                       ['CdParametre', 'NomParametre', 'StParametre', 'LbCourtParametre', 'LbLongParametre']]
            # Tri des lignes du df des paramètres
            df_param.loc[:, 'CdParametre'] = df_param['CdParametre'].astype(int)
            df_param = df_param.sort_values('CdParametre')

            # Elimination de la deuxième ligne du df des groupes
            df_groupes = df_groupes.drop(df_groupes.index[0])
            # Elimination des groupes gelés
            df_groupes = df_groupes[df_groupes['StGroupeParametres'] != 'Gelé']

            # Sélection des colonnes utiles et redéfinition du df des groupes de paramètres
            list_columns = df_groupes.columns.tolist()
            list_columns_new = []
            [list_columns_new.append(nom_col) for nom_col in list_columns if (("@schemeAgencyID" not in nom_col)
                                                                              and ("StGroupeParametres" not in nom_col)
                                                                              and ("NomParametre" not in nom_col)
                                                                              and ("Date" not in nom_col)
                                                                              and ("Auteur" not in nom_col)
                                                                              and ("Com" not in nom_col)
                                                                              and ("DfGroupeParametre" not in nom_col)
                                                                              and ("LbLongGroupeParametres" not in nom_col))]

            list_columns_new.remove("GroupeParametresPere_NomGroupeParametres")
            list_columns_new.insert(0, "GroupeParametresPere_NomGroupeParametres")
            df_groupes = df_groupes[list_columns_new]

            # Remplacement du nom du groupe père par son libellé court
            df_lien_nom_libellecourt = df_groupes.loc[:, ['NomGroupeParametres', 'LbCourtGroupeParametres']]
            df_groupes = df_groupes.merge(df_lien_nom_libellecourt, left_on='GroupeParametresPere_NomGroupeParametres',
                                                                    right_on='NomGroupeParametres', how='left')
            df_groupes = df_groupes.rename(index=str, columns={"LbCourtGroupeParametres_x": "LbCourtGroupeParametres",
                                                               "LbCourtGroupeParametres_y": "LbCourtGroupeParametres_Pere"})
            del df_groupes["GroupeParametresPere_NomGroupeParametres"]
            del df_groupes["NomGroupeParametres_x"]
            del df_groupes["NomGroupeParametres_y"]

            # # Définition et écriture d'un dictionnaire json des groupes et des codes de groupe et listes de paramètres associées
            # df_dict_groupes = df_groupes.copy(deep=True)
            # del df_dict_groupes["LbCourtGroupeParametres_Pere"]
            # df_dict_groupes = df_dict_groupes.set_index(["LbCourtGroupeParametres", "CdGroupeParametres"])
            # df_dict_groupes = df_dict_groupes.dropna(axis='index', how='all')
            # df_dict_groupes["ListCodeParametre"] = df_dict_groupes.fillna('').apply(','.join, axis=1)
            # df_dict_groupes.loc[:, "ListCodeParametre"] = df_dict_groupes["ListCodeParametre"] + ','
            # df_dict_groupes.loc[:, "ListCodeParametre"] = df_dict_groupes["ListCodeParametre"].replace(regex=r',+', value=',').replace(regex=r',$', value='"])').replace(regex=r',', value='", "')
            # df_dict_groupes = df_dict_groupes.reset_index()
            # s_dict_groupes = '"' + df_dict_groupes["LbCourtGroupeParametres"] + '": ("' + df_dict_groupes["CdGroupeParametres"] + '", ["' + df_dict_groupes["ListCodeParametre"] + ","
            # s_dict_groupes.iloc[0] = "{" + s_dict_groupes.iloc[0]
            # s_dict_groupes.iloc[-1] = s_dict_groupes.iloc[-1][:-1] + '}'
            # s_dict_groupes.to_csv(chem_ln_groupe_parametre, index=False, header=False, sep="|", encoding='utf-8', quoting=csv.QUOTE_NONE)

            # Construction et écriture d'un dictionnaire des codes sandre de groupes de paramètres
            df_dict_code_groupe = df_groupes[['LbCourtGroupeParametres', 'CdGroupeParametres']]
            dict_code_groupe = df_dict_code_groupe.set_index('LbCourtGroupeParametres').to_dict()
            dict_code_groupe = dict_code_groupe['CdGroupeParametres']   # pour éliminer ce niveau inutile
            self.pio.ecrire_fichier_json(dict_code_groupe, chem_ln_groupe_code)

            # Recherche des groupes de niveau 1
            del df_groupes["CdGroupeParametres"]
            del df_groupes["GroupeParametresPere_CdGroupeParametres"]
            df_groupes = df_groupes.rename(index=str, columns={"LbCourtGroupeParametres": "Enfant",
                                                               "LbCourtGroupeParametres_Pere": "Pere"})
            df_groupes['Niveau_Enfant'] = 0
            df_groupes['Niveau_Enfant'] = df_groupes['Niveau_Enfant'].apply(lambda x: 11).where(
                (df_groupes['Pere'].isnull()) & (df_groupes['Enfant'] == "Paramètres classés par classe"),
                df_groupes['Niveau_Enfant'])
            df_groupes['Niveau_Enfant'] = df_groupes['Niveau_Enfant'].apply(lambda x: 21).where(
                (df_groupes['Pere'].isnull()) & (df_groupes['Enfant'] == "Paramètres classés par usage"),
                df_groupes['Niveau_Enfant'])
            df_groupes['Niveau_Enfant'] = df_groupes['Niveau_Enfant'].apply(lambda x: 31).where(
                (df_groupes['Pere'].isnull()) & (df_groupes['Enfant'] == "Paramètres classés par textes réglementaires"),
                df_groupes['Niveau_Enfant'])

            # Recherche des groupes de niveau 2, 3 et 4
            tup_niveaux = ((12, 11,
                            22, 21,
                            32, 31),
                           (13, 12,
                            23, 22,
                            33, 32),
                           (14, 13,
                            24, 23,
                            34, 33))
            for tup_niv in tup_niveaux:
                df_jointure = df_groupes.loc[:, ['Enfant', 'Niveau_Enfant']]
                df_groupes = df_groupes.merge(df_jointure, left_on='Pere', right_on='Enfant', how='left')
                df_groupes = df_groupes.rename(index=str, columns={"Enfant_x": "Enfant",
                                                                   "Niveau_Enfant_x": "Niveau_Enfant",
                                                                   "Niveau_Enfant_y": "Niveau_Pere"})
                del df_groupes['Enfant_y']
                df_groupes['Niveau_Enfant'] = df_groupes['Niveau_Enfant'].apply(lambda x: tup_niv[0]).where(
                    df_groupes['Niveau_Pere'] == tup_niv[1], df_groupes['Niveau_Enfant'])
                df_groupes['Niveau_Enfant'] = df_groupes['Niveau_Enfant'].apply(lambda x: tup_niv[2]).where(
                    df_groupes['Niveau_Pere'] == tup_niv[3], df_groupes['Niveau_Enfant'])
                df_groupes['Niveau_Enfant'] = df_groupes['Niveau_Enfant'].apply(lambda x: tup_niv[4]).where(
                    df_groupes['Niveau_Pere'] == tup_niv[5], df_groupes['Niveau_Enfant'])
                del df_groupes['Niveau_Pere']

            # Renommage des colonnes
            df_groupes = df_groupes.rename(index=str, columns={"Enfant": "LbCourtGroupeParametres",
                                                               "Niveau_Enfant": "NiveauGroupeParametres",
                                                               "Pere": "LbCourtGroupePere"})

            # Définition d'un lexique : libellé court du groupe de paramètre / libellé court du groupe père associé
            df_lexique = df_groupes.loc[:, ['LbCourtGroupeParametres', 'LbCourtGroupePere']]

            # Opération de pivot sur le df des groupes - renommage/conversion des colonnes - tri des lignes
            list_columns_ter = df_groupes.columns.tolist()
            list_id_vars = []
            [list_id_vars.append(nom_col) for nom_col in list_columns_ter if "CdParametre" not in nom_col]
            list_value_vars = []
            [list_value_vars.append(nom_col) for nom_col in list_columns_ter if "CdParametre" in nom_col]
            df_groupes = pd.melt(df_groupes, id_vars=list_id_vars, value_vars=list_value_vars)
            del df_groupes["variable"]
            df_groupes = df_groupes.rename(index=str, columns={"value": "CdParametre"})
            df_groupes = df_groupes.dropna(subset=['CdParametre'])
            df_groupes['TypeClassementParametre'] = df_groupes['NiveauGroupeParametres'].astype(str).str.slice(0, 1)
            df_groupes.loc[:, 'TypeClassementParametre'] = df_groupes['TypeClassementParametre'].replace('1', 'Classe').replace('2', 'Usage').replace('3', 'Texte')
            df_groupes = df_groupes.reindex(columns=['TypeClassementParametre', 'CdParametre', 'NiveauGroupeParametres', 'LbCourtGroupeParametres', 'LbCourtGroupePere'])
            df_groupes = df_groupes.sort_values(['TypeClassementParametre', 'CdParametre', 'NiveauGroupeParametres'])

            # On ne garde que les groupes de textes réglementaires "Eaux_Sout" et tous les groupes classe et usage
            df_groupes = df_groupes[(df_groupes['TypeClassementParametre'] != "Texte")
                                    | (df_groupes['LbCourtGroupeParametres'].str.contains("Eaux_Sout"))
                                    | (df_groupes['LbCourtGroupeParametres'].str.contains("Arrete"))]

            # Création des index pour faciliter la sélection ultérieure par loc
            df_groupes = df_groupes.set_index(['TypeClassementParametre', 'NiveauGroupeParametres'])
            df_groupes.loc[:, 'CdParametre'] = df_groupes['CdParametre'].astype(int)

            # Pour chaque couple (type de classement, niveau) :
            # - pivot
            # - concaténation des groupes de classe
            # - fusion avec le df des paramètres
            tup_niveaux = ((('Classe', 11), 'Classe_1'),
                           (('Classe', 12), 'Classe_2'),
                           (('Classe', 13), 'Classe_3'),
                           (('Classe', 14), 'Classe_4'),
                           (('Usage', 21), 'Usage_1'),
                           (('Usage', 22), 'Usage_2'),
                           (('Usage', 23), 'Usage_3'),
                           (('Usage', 24), 'Usage_4'),
                           (('Texte', 31), 'Texte_1'),
                           (('Texte', 32), 'Texte_2'),
                           (('Texte', 33), 'Texte_3'),
                           (('Texte', 34), 'Texte_4'))
            for tup_nv in tup_niveaux:
                try:
                    df_nv = df_groupes.loc[tup_nv[0],]
                    df_nv = df_nv.drop_duplicates()
                    df_nv = df_nv.pivot(index='CdParametre', columns='LbCourtGroupeParametres',
                                        values='LbCourtGroupeParametres')
                    df_nv[tup_nv[1]] = df_nv.fillna('').apply(';'.join, axis=1)
                    df_nv.loc[:, tup_nv[1]] = df_nv[tup_nv[1]].replace(regex=r';+', value='; ').replace(regex=r'^; ', value='').replace(regex=r'; $', value='')
                    df_nv = df_nv.reset_index()
                    df_param = df_param.merge(df_nv.loc[:, ['CdParametre', tup_nv[1]]], on='CdParametre', how='left')
                except:
                    df_param[tup_nv[1]] = ''

            # Ajout des groupes père pour que tous les groupes qui ne contiennent aucun paramètre apparaissent
            # (remplissage des cellules vides à gauche en partant du niveau hiérarchique le plus bas )
            tup_niveaux = (('Classe_4', 'Classe_3'),
                           ('Classe_3', 'Classe_2'),
                           ('Classe_2', 'Classe_1'),
                           ('Usage_4', 'Usage_3'),
                           ('Usage_3', 'Usage_2'),
                           ('Usage_2', 'Usage_1'),
                           ('Texte_4', 'Texte_3'),
                           ('Texte_3', 'Texte_2'),
                           ('Texte_2', 'Texte_1'))
            for tup_nv in tup_niveaux:
                df_split = df_param.loc[:, tup_nv[0]].str.split(';', expand=True)
                df_param[tup_nv[0] + '_split'] = df_split.iloc[:, 0]
                df_param = df_param.merge(df_lexique, left_on=tup_nv[0] + '_split', right_on='LbCourtGroupeParametres',
                                          how='left')
                df_param = df_param.fillna('')
                df_param[tup_nv[1]] = df_param['LbCourtGroupePere'].where(
                    (df_param[tup_nv[0] + '_split'] != '') & (df_param[tup_nv[1]] == ''), df_param[tup_nv[1]])
                del df_param['LbCourtGroupeParametres']
                del df_param['LbCourtGroupePere']
                del df_param[tup_nv[0] + '_split']

            # Fusion avec les paramètres pouvant être saisis dans ADES
            df_param_ades['PARAMETRE_ADES'] = 'oui'
            df_param_ades.loc[:, 'CODE'] = df_param_ades['CODE'].astype(int)
            df_param = df_param.merge(df_param_ades.loc[:, ['CODE', 'PARAMETRE_ADES']], how='left', left_on='CdParametre',
                                      right_on='CODE')
            del df_param['CODE']

            # Fusion avec les unités ADES pour connaître les unités de référence ADES
            df_unites_ades = df_unites_ades.drop_duplicates(['CODE_PARAMETRE'])
            df_unites_ades.loc[:, 'CODE_PARAMETRE'] = df_unites_ades['CODE_PARAMETRE'].astype(int)
            df_param = df_param.merge(df_unites_ades.loc[:, ['CODE_PARAMETRE', 'CODE_UNITE_ADES', 'LIBELLE_UNITE_ADES']],
                                      how='left', left_on='CdParametre', right_on='CODE_PARAMETRE')
            del df_param['CODE_PARAMETRE']

            df_param = df_param.rename(index=str, columns={"CdParametre": "CODE_PARAMETRE",
                                                           "NomParametre": "NOM_PARAMETRE",
                                                           "StParametre": "STATUT_PARAMETRE",
                                                           "LbCourtParametre": "NOM_PARAMETRE_COURT",
                                                           "LbLongParametre": "NOM_PARAMETRE_LONG",
                                                           "Classe_1": "CLASSE_1",
                                                           "Classe_2": "CLASSE_2",
                                                           "Classe_3": "CLASSE_3",
                                                           "Classe_4": "CLASSE_4",
                                                           "Usage_1": "USAGE_1",
                                                           "Usage_2": "USAGE_2",
                                                           "Usage_3": "USAGE_3",
                                                           "Usage_4": "USAGE_4",
                                                           "Texte_1": "REGLEMENT_1",
                                                           "Texte_2": "REGLEMENT_2",
                                                           "Texte_3": "REGLEMENT_3",
                                                           "Texte_4": "REGLEMENT_4"})
            # On ne garde que les paramètres ADES
            df_param = df_param[df_param['PARAMETRE_ADES'] == 'oui']
            df_ln_parametres = df_param

        # Ecriture du fichier csv si le df n'est pas vide
        if len(df_ln_parametres) != 0:
            df_ln_parametres.to_csv(chem_ln_parametre, header=True, index=False, encoding='utf-8', sep=';')

        # Construction du dictionnaire des groupes et écriture du fichier json correspondant
        dict_groupe_parametre = self.construire_dict_groupe_parametre(df_ln_parametres)
        self.pio.ecrire_fichier_json(dict_groupe_parametre, chem_ln_groupe_parametre)

    def construire_dict_groupe_parametre(self, df_ln_parametre):
        """
        Construit un dictionnaire des groupes de paramètres à partir de la liste nationale des paramètres
        construite par la fonction "maj_ln_parametres".
        :param df_ln_parametre: (df) dataframe de la liste natinale des paramètres
        :return: dict
        """
        # Liste des types de colonne à parcourir = type de classement des paramètres au niveau 1
        list_type_groupe = ["CLASSE", "USAGE", "REGLEMENT"]
        dict_groupe_parametre = {}
        # Ajout au dictionnaire de la liste de tous les paramètres
        list_code_parametre = df_ln_parametre['CODE_PARAMETRE'].astype(str).tolist()
        dict_groupe_parametre['Tous les paramètres'] = list_code_parametre
        # Parcours de la liste des types de groupe
        for type_groupe in list_type_groupe:
            # Parcours des 4 niveaux de groupe pour construire la liste des noms de groupe de chaque niveau
            for num_col in range(1, 5):
                nom_col = type_groupe + "_" + str(num_col)
                # Définition de la liste des noms de groupe de chaque niveau
                # (appel de la fonction qui permet d'obtenir une liste complète en splittant chaque nom composé)
                list_nom_groupe = self.extraire_liste_groupe(df_ln_parametre[nom_col])
                # Parcours des noms de groupe de chaque type et niveau de groupe
                for nom_groupe in list_nom_groupe:
                    # Application d'un filtre
                    df_filtre = df_ln_parametre[df_ln_parametre[nom_col].str.contains(nom_groupe, na=False, regex=False)]
                    # Obtention de la liste des code de paramètre associée au filtre
                    list_code_parametre = df_filtre['CODE_PARAMETRE'].astype(str).tolist()
                    # Ajout au dictionnaire des groupes
                    dict_groupe_parametre[nom_groupe] = list_code_parametre
        # Ajout au dictionnaire de la liste des paramètres validés non classés
        df_filtre = df_ln_parametre[(df_ln_parametre['CLASSE_1'].isnull() &
                                     df_ln_parametre['USAGE_1'].isnull() &
                                     df_ln_parametre['REGLEMENT_1'].isnull() &
                                     df_ln_parametre['STATUT_PARAMETRE'].str.contains("Validé", na=False, regex=False)) |
                                    ((df_ln_parametre['CLASSE_1'] == "") &
                                     (df_ln_parametre['USAGE_1'] == "") &
                                     (df_ln_parametre['REGLEMENT_1'] == "") &
                                     (df_ln_parametre['STATUT_PARAMETRE'].str.contains("Validé", na=False, regex=False)))]
        list_code_parametre = df_filtre['CODE_PARAMETRE'].astype(str).tolist()
        dict_groupe_parametre['Paramètres non classés'] = list_code_parametre
        # Ajout au dictionnaire de la liste des paramètres gelés (et nécessairement non classés)
        df_filtre = df_ln_parametre[df_ln_parametre['STATUT_PARAMETRE'].str.contains("Gelé", na=False, regex=False)]
        list_code_parametre = df_filtre['CODE_PARAMETRE'].astype(str).tolist()
        dict_groupe_parametre['Paramètres gelés'] = list_code_parametre
        return dict_groupe_parametre

    def extraire_liste_groupe(self, serie):
        """
        Extrait une liste triée de groupes d'une Series pouvant contenir des groupes multiples
        (niveaux 3 et 4 du Sandre de ln_parametres) : les groupes multiples pour un même niveau
        et un même paramètre sont séparés par ';' et doivent être splittés.
        :param serie: objet Series
        :return: liste python triée
        """
        serie = serie[serie != ""]
        serie = serie.dropna()
        if len(serie) == 0:
            return []
        else:
            serie = serie.str.strip()
            df = serie.str.split('; ', expand=True)
            list_item = []
            for nomcol in df.columns:
                list_item += (df[nomcol].dropna().drop_duplicates().tolist())
                list_item = list(set(list_item))
            list_item.sort()
            return list_item


if __name__ == '__main__':

    print("")
    print("---------------------------------------------------------------")
    print("  Test de la classe Pick_Req du module pick_requete")
    print("---------------------------------------------------------------")
    print("")

    import pick_utilitaire

    # Instanciations de classes PickEau externes au module
    pio = pick_utilitaire.Pick_IO()
    ptools = pick_utilitaire.Pick_Tools()

    # Instanciation de la classe à tester
    preq = Pick_Req(pio, ptools)

    # Impression des chemins et adresses ip
    # print("dossier_plugin : ", preq.dossier_plugin)
    # print("ip_hubeau_niveaux_nappes_stations_csv : ", preq.ip_hubeau_niveaux_nappes_stations_csv)
    # print("ip_hubeau_qualite_nappes_stations_csv : ", preq.ip_hubeau_qualite_nappes_stations_csv)
    # print("ip_sandre_parametres_csv_gz : ",  preq.ip_sandre_parametres_csv_gz)
    # print("ip_sandre_groupes_csv_gz : ", preq.ip_sandre_groupes_csv_gz)
    # print("ip_sandre_masses_eau_csv_gz : ", preq.ip_sandre_masses_eau_csv_gz)
    # print("ip_ades_unites_parametres_support_liquide_xml : ", preq.ip_ades_unites_parametres_support_liquide_xml)
    # print("ip_ades_parametres_xml : ", preq.ip_ades_parametres_xml)

    # # Appel aux fonctions de mise à jour des listes nationales et impression des tailles des df créés
    # chem_ln_parametre_test = os.path.join(preq.dossier_plugin, 'ln_parametres_test.csv')
    # chem_ln_groupe_parametre_test = os.path.join(preq.dossier_plugin, 'ln_groupes_parametres_test.json')
    # chem_ln_groupe_code_test = os.path.join(preq.dossier_plugin, 'ln_groupes_codes_test.json')
    # chem_ln_masses_eau_test = os.path.join(preq.dossier_plugin, 'ln_masses_eau_test.csv')
    # preq.maj_ln_parametres(chem_ln_parametre_test, chem_ln_groupe_parametre_test, chem_ln_groupe_code_test)
    # preq.maj_ln_masses_eau(chem_ln_masses_eau_test)
    # print("chem_ln_parametre_test : ", chem_ln_parametre_test)
    # print("chem_ln_groupe_parametre_test : ", chem_ln_groupe_parametre_test)
    # print("chem_ln_groupe_code_test : ", chem_ln_groupe_code_test)
    # print("chem_ln_masses_eau_test : ", chem_ln_masses_eau_test)

    dossier_plugin = ptools.trouver_dossier_module()
    chem_ln_parametre = os.path.join(dossier_plugin, 'pick_ln_parametres.csv')
    chem_ln_groupe = os.path.join(dossier_plugin, 'ln_groupes_test.json')
    df_ln_parametre = pio.lire_fichier_csv(chem_ln_parametre)
    dict_groupe_parametre = preq.construire_dict_groupe_parametre(df_ln_parametre)
    pio.ecrire_fichier_json(dict_groupe_parametre, chem_ln_groupe)

    # Appel à des requêtes hubeau sur les stations piézo et qualité
    nom_administratif = "Alsace"
    list_dept = ['67', '68']
    df_data, statut_requete = preq.requete_hubeau_par_dept(nom_administratif, list_dept, "stations_qualite_csv")
    print("Stations qualité - Alsace : ", df_data.shape, statut_requete)

    nom_administratif = "08 Ardennes"
    list_dept = ['08']
    df_data, statut_requete = preq.requete_hubeau_par_dept(nom_administratif, list_dept, "stations_qualite_csv")
    print("Stations qualité - 08 Ardennes : ", df_data.shape, statut_requete)

    # Appel à des requêtes hubeau sur les analyses et chroniques piézo
    code_point = "BSS000HRTK"
    list_code_groupe = []    # doit être vide si list_code_parametre n'est pas vide
    list_code_parametre = ["1338"]
    df_data, statut_requete = preq.requete_hubeau_par_point(code_point, list_code_groupe, list_code_parametre, "analyses_qualite_csv")
    print("Analyses qualité - 1338 - BSS000HRTK : ", df_data.shape, statut_requete)

    code_point = "01632X0070/V105"
    list_code_groupe = ["32"]
    list_code_parametre = []    # doit être vide si list_code_groupe n'est pas vide
    df_data, statut_requete = preq.requete_hubeau_par_point(code_point, list_code_groupe, list_code_parametre, "analyses_qualite_csv")
    print("Analyses qualité - 1338 - 01632X0070/V105 : ", df_data.shape, statut_requete)

    code_point = "01632X0070/V105"  # l'API piézo ne connait pas l'id_bss !!!
    list_code_groupe = []   # pas pris en compte dans la requête
    list_code_parametre = []    # pas pris en compte dans la requête
    df_data, statut_requete = preq.requete_hubeau_par_point(code_point, list_code_groupe, list_code_parametre, "chroniques_piezo_csv")
    print("Chroniques piézométriques - piezo - 01632X0070/V105 : ", df_data.shape, statut_requete)
