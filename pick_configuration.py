# -*- coding: utf-8 -*-
"""
@author: Laurent Vaute
email: l.vaute@brgm.fr
copyright: (C) 2019 by BRGM

Module de configuration du plugin PickEau contenant une classe de lecture des fichiers de configuration,
des lexiques et des listes nationales SANDRE et ADES.
"""
import os

class Pick_Config():
    # """
    # Classe de lecture des fichiers de configuration du plugin,
    # des lexiques et des listes nationales SANDRE et ADES.
    # """
    def __init__(self, pio, ptools):
        """
        Constructeur de la classe Pick_Config
        :param pio: instance de la classe Pick_IO du module pick_configuration
        :param ptools:  instance de la classe Pick_Tools du module pick_configuration
        """
        # Définition des chemins des fichiers de configuration, lexiques et listes nationales
        self.dossier_plugin = ptools.trouver_dossier_module()
        self.chem_config_plugin = os.path.join(self.dossier_plugin, 'pick_config_plugin.json')
        self.chem_config_user = os.path.join(self.dossier_plugin, 'pick_config_user.json')
        chem_lexique = os.path.join(self.dossier_plugin, 'pick_lexiques.json')
        chem_ln_parametre = os.path.join(self.dossier_plugin, 'pick_ln_parametres.csv')
        chem_ln_groupe_parametre = os.path.join(self.dossier_plugin, 'pick_ln_groupes_parametres.json')
        chem_ln_groupe_code = os.path.join(self.dossier_plugin, 'pick_ln_groupes_codes.json')

        # Lecture de fichiers externes : fichiers de configuration
        self.dict_config_plugin = pio.lire_fichier_json(self.chem_config_plugin)
        self.dict_config_user = pio.lire_fichier_json(self.chem_config_user)

        # Définition des dossiers de travail
        self.dossier_travail_user = self.dict_config_user["dossier_travail_user"]
        self.dossier_travail_defaut = self.dict_config_plugin["dossier_travail_defaut"]

        # Lecture de fichiers externes : listes nationales et lexiques
        self.dict_lexique = pio.lire_fichier_json(chem_lexique)
        self.dict_administratif = self.dict_lexique['lex_administratif']
        self.df_lex_parametre = pio.lire_fichier_csv(chem_ln_parametre)
        self.df_lex_parametre['NOM_LEXIQUE'] = self.df_lex_parametre['NOM_PARAMETRE_LONG'] + " | " + self.df_lex_parametre['CODE_PARAMETRE'].astype(str)
        self.df_lex_parametre = self.df_lex_parametre[self.df_lex_parametre['PARAMETRE_ADES'] == 'oui']
        self.dict_groupe_pickeau_qualite = self.dict_lexique['lex_groupe_parametre_pickeau']
        self.dict_groupe_parametre_qualite = pio.lire_fichier_json(chem_ln_groupe_parametre)
        self.dict_groupe_code_qualite = pio.lire_fichier_json(chem_ln_groupe_code)

        # Définition des lexiques de PickEau
        self.list_lex_type_point = self.dict_lexique['lex_type_point']
        self.list_lex_administratif = list(self.dict_administratif.keys())
        self.list_lex_bassin = self.dict_lexique['lex_bassin']
        self.list_lex_parametre_quantite = self.dict_lexique['lex_parametre_quantite']
        self.list_lex_groupe_parametre_pickeau = self.dict_groupe_pickeau_qualite.keys()
        self.list_lex_groupe_parametre_sandre_1 = self.dict_lexique['lex_groupe_sandre_1']
        self.list_lex_tendance = self.dict_lexique['lex_tendance']
        self.list_lex_type_commentaire = self.dict_lexique['lex_type_commentaire']
        self.list_lex_commentaire_pickeau = self.dict_lexique['lex_commentaire_pickeau']
        self.list_lex_qualification_ades = self.dict_lexique['lex_qualification_ades']
        self.list_lex_disposition_graphe = self.dict_lexique['lex_disposition_graphe']

if __name__ == '__main__':

    # ================== TEST Pick_Config =====================

    print("")
    print("------------------------------------------------------------")
    print("  Test de la classe Pick_Config du module pick_configuration")
    print("------------------------------------------------------------")
    print("")

    import pick_utilitaire

    # Instanciations de classes PickEau externes au module
    pio = pick_utilitaire.Pick_IO()
    ptools = pick_utilitaire.Pick_Tools()

    # Instanciation de la classe à tester
    pconfig = Pick_Config(pio, ptools)

    print("dossier_plugin : ", pconfig.dossier_plugin)
    print("df_lex_parametres : ", pconfig.df_ln_parametre.shape)
    print('dict_administratif["Auvergne-Rhône-Alpes"][0] : ', pconfig.dict_administratif["Auvergne-Rhône-Alpes"][0]) # il s'agit bien d'un dictionnaire de listes de listes de dept
    print("list_type_point : ", pconfig.list_lex_type_point)
    print("list_tendances : ", pconfig.list_lex_tendance)
    print("list_bassins : ", pconfig.list_lex_bassin)
    print("list_administratif : ", pconfig.list_lex_administratif)

    # Lecture et écriture d'un fichier json de configuration
    pio.lire_fichier_json(pconfig.chem_config_plugin)
    print("Lecture du dictionnaire contenu dans le fichier de configuration du plugin : ", pconfig.chem_config_plugin)
    pconfig.dict_config_plugin["dossier_plugin_defaut"] = pconfig.dossier_plugin
    print("Définition du chemin du dossier par défaut : ", pconfig.dossier_plugin)
    pio.ecrire_fichier_json(pconfig.dict_config_plugin, pconfig.chem_config_plugin)
    print("Ecriture du dictionnaire modifié dans le fichier de configuration du plugin")
