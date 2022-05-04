# -*- coding: utf-8 -*-
"""
@author: Laurent Vaute
email: l.vaute@brgm.fr
copyright: (C) 2019 by BRGM

Module de fonctions utilitaires regroupées dans les classes Pick_IO et Pick_Tools :
    - Pick_IO : lecture / écriture de fichiers externes (json, csv, hdf),
    - Pick_Tools : fonctions utilitaires diverses.
"""

import os
import json
import pandas as pd
import xlwings as xw


class Pick_IO():
    """
    Classe de fonctions de lecture / écriture de fichiers externes (json, csv, hdf).
    """
    def __init__(self):
        pass

    def lire_fichier_csv(self, chem_fichier):
        """
        Lit un fichier csv encodé en utf-8 avec séparateur ;
        :param chem_fichier: chemin du fichier csv
        :return: dataframe du fichier csv
        """
        df_csv = pd.read_csv(chem_fichier, sep=';', encoding='utf-8')
        return df_csv

# def lireFichierCsv(self, chemin_fichier):
#     """
#     Lit le fichier CSV table des matières dont le chemin complet est passé en paramètre.
#     """
#     try:
#         df_infos_fichier_out = pd.read_csv(chemin_fichier, encoding='mbcs', sep=';')
#         # df_infos_fichier_out['Time'] = pd.to_datetime(df_infos_fichier_out['Time'], format= '%Y/%m/%d')
#         # Retour du df en sortie de la fonction
#         return df_infos_fichier_out
#     except:
#         raise FileNotFoundError

    def ecrire_fichier_csv(self, df, chem_fichier):
        """
        Ecrit un fichier csv encodé en utf-8 avec séparateur ;
        :param chem_fichier: chemin du fichier csv
        :return: None
        """
        df.to_csv(chem_fichier, sep=';', header=True, index=False, encoding='utf-8', mode='w', decimal='.', float_format='%g')

    def lire_fichier_json(self, chem_fichier):
        """
        Lit un fichier json encodé en utf-8
        :param chem_fichier: chemin du fichier json
        :return: dictionnaire du fichier json
        """
        with open(chem_fichier, 'r', encoding='utf-8') as f:
            dict_json = json.load(f)
        return dict_json

    def ecrire_fichier_json(self, data, chem_fichier):
        """
        Ecrit un fichier json encodé en utf-8
        :param chem_fichier: chemin du fichier json
        :return: None
        """
        with open(chem_fichier, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4, sort_keys=False)

    def ecrire_table_hdf(self, chem_hdf, nom_table_hdf, df_data):
        """
        Ecrit un dataframe sous forme de table requêtable dans un fichier hdf compressé
        :param chem_fichier: chemin du fichier hdf (il est créé s'il n'existe pas)
        :return: None
        """
        df_data.to_hdf(chem_hdf,
                       nom_table_hdf,
                       format='table',
                       append=False,
                       data_columns=True,
                       complevel=9,
                       complib='blosc')

    def lire_table_hdf(self, chem_hdf, nom_table_hdf):
        """
        Lit une table d'un fichier hdf compressé et renvoie un dataframe de la table
        :param chem_fichier: chemin du fichier hdf
        :return: None
        """
        # Lecture des données du paramètre dans le fichier hdf
        df_data = pd.read_hdf(chem_hdf, nom_table_hdf)

    def ecrire_fichier_excel(self, df, chemin_fichier, nom_feuille, nouveau_fichier=True, nouvelle_feuille=True):
        if nouveau_fichier == True:
            # Création d'un nouveau classeur Excel
            wb_excel = xw.Book()
        else:
            wb_excel = xw.Book(chemin_fichier)
        if nouvelle_feuille == True:
            # Ajout d'une nouvelle feuille au classeur Excel
            wb_excel.sheets.add(nom_feuille)
        wb_excel.sheets(nom_feuille).range("A1").options(index=False).value = df
        wb_excel.save(chemin_fichier)

    @staticmethod
    def lire_fichier_text(chem_fichier: str):
        """
        Lit un fichier text
        :param chem_fichier: str -- chemin absolu du fichier
        """
        file = open(chem_fichier, "r")
        with open(chem_fichier) as f:
            contenu_fichier: str = f.read()
            return contenu_fichier


class Pick_Tools():
    """
    Classe de fonctions utilitaires diverses.
    """
    def __init__(self):
        pass

    def trouver_dossier_module(self):
        """
        Renvoie le chemin absolu du dossier dans lequel se trouve ce module
        :return: chemin absolu (str)
        """
        path = os.path.abspath(__file__)
        dir_path = os.path.dirname(path)
        return dir_path

    @staticmethod
    def lire_fichier_config() -> dict:
        pickTools = Pick_Tools()
        dir_path = pickTools.trouver_dossier_module()
        rel_path = 'configs/default_config.json'
        abs_path_config = os.path.join(dir_path, rel_path)
        pickIo = Pick_IO()
        config: dict = pickIo.lire_fichier_json(abs_path_config)
        return config

#
# def ouvrirFichierCsvDansExcel(self, chemin_fichier):
#     """
#     Ouvre dans Excel le fichier dont le chemin complet est passé en paramètre.
#     """
#     try:
#         # Utilisation de la librairie xlwings pour éviter le pb de trouver l'emplacement de Excel.exe
#         wb = xw.Book(chemin_fichier)
#         # chemin_Excel = "C:\Program Files (x86)\Microsoft Office\Office16\EXCEL.EXE"
#         # commande = chemin_Excel + " " + chemin_fichier
#         # subprocess.Popen(commande)  # Popen = démarre un nouveau processus = non bloquant pour QGis
#         #                             # run = ouvre l'exécutable dans le même processus = bloquant pour QGis
#     except:
#         raise FileNotFoundError
#
# def calculerNbLignesFichierTexte(self, chemin_fichier):
#     """
#     Calcule le nombre de lignes d'un fichier texte dont le chemin est passé en paramètre
#     """
#     # my_timer = Timer()
#     # 2m28' pour un chasim.out de 10 Go
#     try:
#         nb_lignes_fichier_out = sum((1 for i in open(chemin_fichier, 'rb')))
#         return nb_lignes_fichier_out
#     except:
#         raise FileNotFoundError
#
#     # temps_calcul = my_timer.get_time_hhmmss()
#     # raise Exception("ARRET CALCUL POUR DEBUG")
#
# def supprimerFichierParShellWindows(self, chemin_fichier):
#     """
#     Supprime le fichier dont le chemin complet est passé en paramètre.
#     """
#     try:
#         myenv = os.environ.copy()
#         myenv['GDAL_PAM_ENABLED'] = 'NO'
#         command = "del " + chemin_fichier
#         subprocess.run(command, env=myenv, shell=True)
#         # subprocess.run(commande, shell=True)    # Popen = démarre un nouveau processus = non bloquant pour QGis
#         #                                         # run = ouvre l'exécutable dans le même processus = bloquant pour QGis
#         #
#         # Modifier l'environnement du processus fils pour éviter que GDAL ne crée un fichier .aux.xml à chaque
#         # suppression d'une couche :
#         #
#         # Make a copy of the environment and pass is to the childen.
#         # You have total control over the children environment and won't affect python's own environment
#         #
#         # myenv = os.environ.copy()
#         # myenv['LD_LIBRARY_PATH'] = 'my_path'
#         # command = ['sqsub', '-np', var1, '/homedir/anotherdir/executable']
#         # subprocess.check_call(command, env=myenv)
#     except:
#         raise FileNotFoundError



if __name__ == '__main__':

    print("")
    print("-------------------------------------------------------------------")
    print("  Test de la classe Pick_IO du module pick_utilitaire")
    print("-------------------------------------------------------------------")
    print("")

    # Instanciation de la classe
    pio = Pick_IO()

    print("variable : ", "")

    print("")
    print("-------------------------------------------------------------------")
    print("  Test de la classe Pick_Tools du module pick_utilitaire")
    print("-------------------------------------------------------------------")
    print("")

    # Instanciation de la classe à tester
    ptools = Pick_Tools()

    print("dossier_module : ", ptools.trouver_dossier_module())
