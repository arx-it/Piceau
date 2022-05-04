# -*- coding: utf-8 -*-
"""
@author: Laurent Vaute
email: l.vaute@brgm.fr
copyright: (C) 2019 by BRGM

Module de test de tous les modules et classes du plugin PickEau
"""

import os
import pick_utilitaire
import pick_configuration
import pick_requete
import pick_page_donnee
import pick_page_graphique
import pick_page_traitement
import pick_page_commentaire


def test_module_pick_utilitaire():

    print("")
    print("-----------------------------------------------------")
    print("  Test de la classe Pick_IO du module pick_utilitaire")
    print("-----------------------------------------------------")
    print("")

    print("")
    print("--------------------------------------------------------")
    print("  Test de la classe Pick_Tools du module pick_utilitaire")
    print("--------------------------------------------------------")
    print("")


def test_module_pick_configuration():

    print("")
    print("------------------------------------------------------------")
    print("  Test de la classe Pick_Config du module pick_configuration")
    print("------------------------------------------------------------")
    print("")

    pio = pick_utilitaire.Pick_IO()
    ptools = pick_utilitaire.Pick_Tools()
    pconfig = pick_configuration.Pick_Config(pio, ptools)

    print("dossier_plugin : ", pconfig.dossier_plugin)
    print("df_masses_eau : ", pconfig.df_ln_masse_eau.shape)
    print("df_lex_parametres : ", pconfig.df_ln_parametre.shape)
    print('dict_zones_geo["Auvergne-Rhône-Alpes"][0] : ', pconfig.dict_zone_geo["Auvergne-Rhône-Alpes"][0]) # il s'agit bien d'un dictionnaire de listes de listes de dept
    print("list_type_point : ", pconfig.list_lex_type_point)
    print("list_tendances : ", pconfig.list_lex_tendance)
    print("list_bassins : ", pconfig.list_lex_bassin)
    print("list_zones_geo : ", pconfig.list_lex_zone_geo)

    # Lecture et écriture d'un fichier json de configuration
    pio.lire_fichier_json(pconfig.chem_config_plugin)
    print("Lecture du dictionnaire contenu dans le fichier de configuration du plugin : ", pconfig.chem_config_plugin)
    pconfig.dict_config_plugin["dossier_plugin_defaut"] = pconfig.dossier_plugin
    print("Définition du chemin du dossier par défaut : ", pconfig.dossier_plugin)
    pio.ecrire_fichier_json(pconfig.dict_config_plugin, pconfig.chem_config_plugin)
    print("Ecriture du dictionnaire modifié dans le fichier de configuration du plugin")


def test_module_pick_requete():

    print("")
    print("---------------------------------------------------")
    print("  Test de la classe Pick_Req du module pick_requete")
    print("---------------------------------------------------")
    print("")

    pio = pick_utilitaire.Pick_IO()
    ptools = pick_utilitaire.Pick_Tools()
    preq = pick_requete.Pick_Req(pio, ptools)

    # Impression des chemins et adresses ip
    print("dossier_plugin : ", preq.dossier_plugin)
    print("ip_hubeau_niveaux_nappes_stations_csv : ", preq.ip_hubeau_niveaux_nappes_stations_csv)
    print("ip_hubeau_qualite_nappes_stations_csv : ", preq.ip_hubeau_qualite_nappes_stations_csv)
    print("ip_sandre_parametres_csv_gz : ",  preq.ip_sandre_parametres_csv_gz)
    print("ip_sandre_groupes_csv_gz : ", preq.ip_sandre_groupes_csv_gz)
    print("ip_sandre_masses_eau_csv_gz : ", preq.ip_sandre_masses_eau_csv_gz)
    print("ip_ades_unites_parametres_support_liquide_xml : ", preq.ip_ades_unites_parametres_support_liquide_xml)
    print("ip_ades_parametres_xml : ", preq.ip_ades_parametres_xml)

    # Appel aux fonctions de mise à jour des listes nationales et impression des tailles des df créés
    chem_ln_parametres_test = os.path.join(preq.dossier_plugin, 'ln_parametres_test.csv')
    chem_ln_masses_eau_test = os.path.join(preq.dossier_plugin, 'ln_masses_eau_test.csv')
    df_ln_parametres = preq.maj_ln_parametres(chem_ln_parametres_test)
    df_ln_masses_eau = preq.maj_ln_masses_eau(chem_ln_masses_eau_test)
    print("chem_ln_parametres_test : ", chem_ln_parametres_test)
    print("chem_ln_masses_eau_test : ", chem_ln_masses_eau_test)
    print("df_ln_parametres : ", df_ln_parametres.shape)
    print("df_ln_masses_eau : ", df_ln_masses_eau.shape)

    # Appel à des requêtes hubeau sur les stations piézo et qualité
    nom_zone_geo = "Auvergne-Rhône-Alpes"
    list_list_dept = [['03', '15', '43', '63'], ['01', '07', '26', '38', '42', '69', '73', '74']]
    df_data, statut_requete = preq.requete_hubeau_par_dept(nom_zone_geo, list_list_dept, "stations_qualite_csv")
    print("Stations qualité - Auvergne-Rhône-Alpes : ", df_data.shape, statut_requete)

    nom_zone_geo = "Alsace"
    list_list_dept = [['67', '68']]
    df_data, statut_requete = preq.requete_hubeau_par_dept(nom_zone_geo, list_list_dept, "stations_qualite_csv")
    print("Stations qualité - Alsace : ", df_data.shape, statut_requete)

    nom_zone_geo = "08 Ardennes"
    list_list_dept = [['08']]
    df_data, statut_requete = preq.requete_hubeau_par_dept(nom_zone_geo, list_list_dept, "stations_qualite_csv")
    print("Stations qualité - 08 Ardennes : ", df_data.shape, statut_requete)

    nom_zone_geo = "Toute la France"    # Quelle que soit la valeur choisie, la méthode ne tient pas compte des départements (non géré par Hubeau et moins de 5000 points en France)
    list_list_dept = [['67', '68'], ['08', '10', '51', '52'], ['54', '55', '57', '88'], ['24', '33', '40', '47', '64'], ['19', '23', '87'], ['16', '17', '7', '86'], ['03', '15', '43', '63'], ['01', '07', '26', '38', '42', '69', '73', '74'], ['14', '50', '61'], ['27', '76'], ['21', '58', '71', '89'], ['25', '39', '70', '90'], ['22', '29', '35', '56'], ['18', '28', '36', '37', '41', '45'], ['2A', '2B'], ['971', '972', '973', '974', '975', '976'], ['75', '77', '78', '91', '92', '93', '94', '95'], ['11', '30', '34', '48', '66'], ['09', '12', '31', '32', '46', '65', '81', '82'], ['59', '62'], ['02', '60', '80'], ['44', '49', '53', '72', '85'], ['04', '05', '06', '13', '83', '84'], ['984', '986', '987']]
    df_data, statut_requete = preq.requete_hubeau_par_dept(nom_zone_geo, list_list_dept, "stations_piezo_csv")
    print("Stations piézo - Toute la France : ", df_data.shape, statut_requete)

    # Appel à des requêtes hubeau sur les analyses et chroniques piézo
    code_parametre = "1338"
    list_list_point = [["BSS000HRTK"], ["BSS000HSBU", "BSS000KPLT"]]    # id_bss
    df_data, statut_requete = preq.requete_hubeau_par_point(code_parametre, list_list_point, "analyses_qualite_csv")
    print("Analyses qualité - 1338 - 3 points BFL : ", df_data.shape, statut_requete)
    list_list_point = [["01632X0070/V105"], ["01137X0175/N05", "01377X0211/S14"]]   # ou code_bss
    df_data, statut_requete = preq.requete_hubeau_par_point(code_parametre, list_list_point, "analyses_qualite_csv")
    print("Analyses qualité - 1338 - 3 points BFL : ", df_data.shape, statut_requete)

    code_parametre = "piezo"
    list_list_point = [["01632X0070/V105"], ["01137X0175/N05", "01377X0211/S14"]]   # l'API piézo ne connait pas l'id_bss !!!
    df_data, statut_requete = preq.requete_hubeau_par_point(code_parametre, list_list_point, "chroniques_piezo_csv")
    print("Chroniques piézométriques - piezo - 3 points BFL : ", df_data.shape, statut_requete)


def test_module_pick_donnee():

    pass


def test_module_pick_graphique():

    pass


def test_module_pick_traitement():

    pass


def test_module_pick_commentaire():

    pass


if __name__ == '__main__':

    test_module_pick_configuration()
    test_module_pick_requete()
    test_module_pick_donnee()
    test_module_pick_graphique()
    test_module_pick_traitement()
    test_module_pick_commentaire()

