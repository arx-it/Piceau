# -*- coding: utf-8 -*-
"""
@author: Laurent Vaute
email: l.vaute@brgm.fr
copyright: (C) 2019 by BRGM

TODO:
    - Le dictionnaire des groupes de paramètres utilisé pour lancer les requêtes chimie Sandre est incomplet
      car il ne présente pas les groupes ne contenant que des groupes de niveau inférieur !
      --> utiliser le filtre de la liste nationale des paramètres ou compléter le dictionnaire lors de sa création.
    - Conserver le numéro des groupes dans le dictionnaire des groupes s'il est utilisé.
    - Présenter dans les listes déroulantes les paramètres non classés et les paramètres gelés sans classe aujourd'hui.
    - Gérer le problème important des unités multiples dans ADES : indexer sur le couple code paramètre / code unité ?
    - Renseigner les métadonnées de la couche avec les infos de sélection de points et paramètres + affichage
      dans le plugin.
    - Afficher en dynamique le nombre de couples points - paramètres sélectionnés.

Module PickEau :
    - sélection des points d'eau,
    - téléchargement et affichage des stations de mesure (points d'eau) sur la carte,
    - sélection des paramètres,
    - téléchargement, affichage sur la carte et stockage des données reçues.
"""

from PyQt5.QtWidgets import QDockWidget, QAction, QFileDialog, QMessageBox
from PyQt5.QtCore import QCoreApplication
from qgis.core import *
from qgis.gui import QgsProjectionSelectionWidget
from osgeo import ogr

from .zone_etude.zone_etude import ZoneEtude
from .donnees.donnees_calculs import DonneesCalculs
# from .donnees.outils_layers import OutilsLayers
from .utilitaires.utilitaire_couches import UtilitaireCouches
import os
import datetime
import pandas as pd
from urllib.parse import quote


# Définition des exceptions gérées par les fonctions des classes du module
class Error(Exception):
    """Base class for other exceptions."""
    pass


class ErreurInterruptionUtilisateur(Error):
    """Exception gérée levée lorsque l'utilisateur a interrompu le calcul en cours."""
    pass


class ErreurResultatRequeteIncorrect(Error):
    """Exception gérée levée lorsque le résultat d'une requête est incorrect."""
    pass


class ErreurListWidgetPointVide(Error):
    """Exception gérée levée lorsque le listWidget des points est vide."""
    pass


class ErreurListWidgetParametreVide(Error):
    """Exception gérée levée lorsque le listWidget des paramètres est vide."""
    pass


class ErreurExistenceDossierResultat(Error):
    """Exception gérée levée lorsque le dossier devant contenir les résultats n'existe pas."""
    pass


class ErreurCreationSousDossierResultat(Error):
    """Exception gérée levée lorsque le sous-dossier devant contenir les résultats ne peut pas être créé."""
    pass


class ErreurCreationCoucheQgis(Error):
    """Exception gérée levée lorsque la couche Qgis n'a pas pu être créée à partir du fichier source."""
    pass


class ErreurCoucheQgisNonConforme(Error):
    """Exception gérée levée si la couche Qgis n'est pas issue d'une requête Hubeau de téléchargement de points."""
    pass


class ErreurNombreParametreQualiteTropGrand(Error):
    """Exception gérée levée s'il y a trop de paramètres quantité à télécharger (> 200)."""
    pass


class ErreurNombreGroupeQualiteTropGrand(Error):
    """Exception gérée levée s'il y a trop de paramètres qualité à télécharger (> 200)."""
    pass


class ErreurListeParametreQuantiteIncorrecte(Error):
    """Exception gérée levée si la liste des paramètres quantité est incorrecte."""
    pass


class ErreurListeParametreQualiteIncorrecte(Error):
    """Exception gérée levée si la liste des groupes ou paramètres quantité est incorrecte."""
    pass


class ErreurAucuneCoucheSelectionnee(Error):
    """Exception gérée levée si aucune couche Qgis n'est sélectionnée."""
    pass


class ErreurAucuneStationSelectionnee(Error):
    """Exception gérée levée si aucune station de la couche de stations Hubeau active
      n'est sélectionnée (ou que les attributs sont manquants)."""
    pass


class ErreurExistenceDossierGeopackage(Error):
    """Exception gérée levée si le dossier contenant le geopackage de la couche courante n'existe pas."""
    pass


class ErreurExistenceFichierGeopackage(Error):
    """Exception gérée levée si le fichier geopackage contenant la couche courante n'existe pas."""
    pass


class Pick_Pg_Data():
    """
    Classe liée à la page 1 de l'objet tabWidget de l'interface de PickEau :
        - sélection des points d'eau,
        - téléchargement et affichage des points d'eau sur la carte,
        - sélection des paramètres,
        - téléchargement, affichage sur la carte et stockage des données reçues.
    Cette classe prend en paramètres plusieurs instances des modules de PickEau :
        - pickeau_dockwidget.PickEauDockWidget : widget qt contenant les objets de l'interface de PickEau
        - pick_configuration.Pick_Config : fonctions de configuration du plugin PickEau
        - pick_requete.Pick_Req : fonctions d'envoi de requêtes sur les serveurs Hubeau, Sandre, Ades
        - pick_utilitaire.Pick_IO : fonctions de lecture / écriture de fichiers externes
        - pick_utilitaire.Pick_Tools : fonctions utilitaires diverses
    """

    def __init__(self, iface, dockwidget, pio, ptools, pconfig, preq):

        # Définition des attributs de la classe = objets de la classe PickEau passés en paramètre
        self.iface = None   # pour éviter les problèmes au rechargement du plugin (https://gis.stackexchange.com/questions/289330/passing-self-when-calling-functions-in-modules-from-other-modules-using-pyqgis)
        self.iface = iface
        self.pconfig = pconfig
        self.preq = preq
        self.pio = pio
        self.ptools = ptools
        self.dockwidget = dockwidget
        self.stop = False

        DonneesCalculs(dockwidget, iface)  # init donnees calculs

        # Désactivation des widgets non encore implémentés
        self.dockwidget.cbx_choisirPointBassin.setEnabled(False)
        self.dockwidget.pbt_ajouterPointBassin.setEnabled(False)
        self.dockwidget.le_saisirCodeSandre.setEnabled(False)
        self.dockwidget.pbt_ajouterCodeSandre.setEnabled(False)

        # Connexion ou initialisation des widgets de la page (la liste est complète et doit le rester pour référence)
        self.dockwidget.tb_choisirDossierResultat.clicked.connect(self.choisir_dossier_resultat)
        # self.dockwidget.le_afficherDossierResultat
        self.dockwidget.qgs_projection.setCrs(QgsCoordinateReferenceSystem('EPSG:2154'))
        self.dockwidget.qgs_projection.setOptionVisible(QgsProjectionSelectionWidget.CurrentCrs, True)
        self.dockwidget.cbx_choisirTypePoint.addItems(self.pconfig.list_lex_type_point)
        self.dockwidget.cbx_choisirPointAdministratif.addItems(self.pconfig.list_lex_administratif)
        self.dockwidget.pbt_ajouterPointAdministratif.clicked.connect(self.ajouter_point_administratif)
        self.dockwidget.cbx_choisirPointBassin.addItems(self.pconfig.list_lex_bassin)
        self.dockwidget.pbt_ajouterPointBassin.clicked.connect(self.ajouter_point_bassin)
        # self.dockwidget.listw_afficherItemSelectionPoint
        self.dockwidget.pbt_supprimerItemSelectionPoint.clicked.connect(self.supprimer_point)
        self.dockwidget.pbt_viderListItemSelectionPoint.clicked.connect(self.vider_list_point)
        self.dockwidget.pbt_telechargerPoints.clicked.connect(self.telecharger_point)
        # self.dockwidget.cbx_choisirParametreQuantite.addItems(self.pconfig.list_lex_parametre_quantite)
        # self.dockwidget.pbt_ajouterParametreQuantite.clicked.connect(self.ajouter_parametre_quantite)
        self.dockwidget.cbx_choisirParametreGroupePickEau.addItems(self.pconfig.list_lex_groupe_parametre_pickeau)
        self.dockwidget.cbx_choisirParametreGroupePickEau.activated.connect(self.choisir_groupe_parametre_pickeau)
        self.dockwidget.pbt_ajouterParametreGroupePickEau.clicked.connect(self.ajouter_parametre_groupe_pickeau)
        self.dockwidget.cbx_choisirParametreGroupe1.addItems(self.pconfig.list_lex_groupe_parametre_sandre_1)
        self.dockwidget.cbx_choisirParametreGroupe1.activated.connect(self.choisir_groupe_parametre_1)
        self.dockwidget.pbt_ajouterParametreGroupe1.clicked.connect(self.ajouter_parametre_groupe_1)
        self.dockwidget.cbx_choisirParametreGroupe2.activated.connect(self.choisir_groupe_parametre_2)
        self.dockwidget.pbt_ajouterParametreGroupe2.clicked.connect(self.ajouter_parametre_groupe_2)
        self.dockwidget.cbx_choisirParametreGroupe3.activated.connect(self.choisir_groupe_parametre_3)
        self.dockwidget.pbt_ajouterParametreGroupe3.clicked.connect(self.ajouter_parametre_groupe_3)
        self.dockwidget.cbx_choisirParametreGroupe4.activated.connect(self.choisir_groupe_parametre_4)
        self.dockwidget.pbt_ajouterParametreGroupe4.clicked.connect(self.ajouter_parametre_groupe_4)
        # self.dockwidget.cbx_choisirParametre.addItems()
        self.dockwidget.pbt_ajouterParametre.clicked.connect(self.ajouter_parametre_parametre)
        # self.dockwidget.le_saisirCodeSandre
        self.dockwidget.pbt_ajouterCodeSandre.clicked.connect(self.ajouter_parametre_code_sandre)
        # self.dockwidget.listw_afficherItemSelectionParametre
        self.dockwidget.pbt_supprimerItemSelectionParametre.clicked.connect(self.supprimer_parametre)
        self.dockwidget.pbt_viderListItemSelectionParametres.clicked.connect(self.vider_list_parametre)
        self.dockwidget.pbt_telechargerData.clicked.connect(self.telecharger_data)
        self.dockwidget.progressBar.reset()
        self.dockwidget.progressBarStations.reset()
        self.dockwidget.pb_annuler.clicked.connect(self.stop_iteration)
        self.dockwidget.pb_annuler.setEnabled(False)
        self.dockwidget.pb_annulerStations.clicked.connect(self.stop_iteration)
        self.dockwidget.pb_annulerStations.setEnabled(False)

        self.dockwidget.pbt_telechargerData_pizo.clicked.connect(self.telecharger_data_piezometre)

        # __________Zone etude favorite______________________________________________________________________________
        plugin_dir = os.path.dirname(__file__)
        zoneEtude = ZoneEtude(self.iface.mapCanvas(), plugin_dir, self.dockwidget)

    def choisir_dossier_resultat(self):
        """
        [ Connectée à 'tb_choisirDossierResultat' ]
        Permet de choisir ou de saisir le nom d'un dossier résultat existant.
        """
        chemin_dossier_resultat = str(QFileDialog.getExistingDirectory(
                                      caption="Sélectionnez un dossier pour écrire les données téléchargées"))
        if (chemin_dossier_resultat is not None) and (chemin_dossier_resultat != ""):
            # Affiche le nom du dossier choisi par l'utilisateur dans la ligne de texte associée
            self.dockwidget.le_afficherDossierResultat.setText(chemin_dossier_resultat)

    def ajouter_point_administratif(self):
        nom_item = self.dockwidget.cbx_choisirPointAdministratif.currentText()
        self.dockwidget.listw_afficherItemSelectionPoint.addItem("Administratif - " + nom_item)

    def ajouter_point_bassin(self):
        nom_item = self.dockwidget.cbx_choisirPointBassin.currentText()
        self.dockwidget.listw_afficherItemSelectionPoint.addItem("Bassin - " + nom_item)

    def supprimer_point(self):
        index_item = self.dockwidget.listw_afficherItemSelectionPoint.currentRow()
        self.dockwidget.listw_afficherItemSelectionPoint.takeItem(index_item)

    def vider_list_point(self):
        self.dockwidget.listw_afficherItemSelectionPoint.clear()

    def telecharger_point(self):

        # Définition du flag d'interruption des boucles de requete par appui sur le bouton 'Interrompre'
        self.stop = False
        # L'ensemble de la fonction est incluse dans un bloc try de niveau le plus haut pour capturer
        # tous les types d'erreurs gérés (par "raise") : chaque erreur gérée rencontrée est remontée
        # jusqu'à ce niveau et passée au bloc "except" correspondant (voir en bas de la fonction).
        # Il est possible d'insérer des structures try - except de niveau inférieur, chaque except de niveau
        # inférieur devant lever par "raise" une exception gérée qui remontera jusqu'au niveau supérieur.
        try:
            # Détermination du type de point d'eau (piézo ou qualito)
            type_point = self.dockwidget.cbx_choisirTypePoint.currentText()
            # Traitement des informations écrites par l'utilisateur dans la listwidget
            list_item = self.obtenir_liste_item_listwidget(self.dockwidget.listw_afficherItemSelectionPoint)
            # Vérification de l'existence du dossier résultat --> si absent = erreur
            chemin_dossier_resultat = self.dockwidget.le_afficherDossierResultat.text()
            if not os.path.isdir(chemin_dossier_resultat):
                raise ErreurExistenceDossierResultat
            # Vérification de la présence d'items dans la liste --> si vide = erreur
            if len(list_item) == 0:
                raise ErreurListWidgetPointVide
            # Renvoie le crs sélectionné par l'utilisateur (objet)
            crs_reproj = self.dockwidget.qgs_projection.crs()
            # Renvoie le crs (p.ex sous la forme "EPSG:2154")
            epsg_reproj = crs_reproj.authid()
            # # On en extrait le code epsg et on le convertit en entier
            # code_epsg_reproj = int(crs_reproj.authid()[5:])
            # Elimination des doublons de la liste
            list_item = list(set(list_item))
            # Boucle de remplissage d'un dictionnaire avec les informations nécessaires pour construire les requêtes
            dict_item = {}
            nb_req = 0
            for item in list_item:
                # Traitement du texte de chaque item pour obtenir le type et le nom d'item,
                # ainsi que la liste de liste de depts associée et le nb de requêtes correspondant
                type_item = item.split(" - ")[0]
                nom_item = item.split(" - ")[1]
                if type_item == "Administratif":
                    list_list_dept = self.pconfig.dict_administratif[nom_item]
                    dict_item[item] = (type_item, nom_item, list_list_dept)
                    nb_req += len(list_list_dept)
                # TODO : traiter les autres type_item
                elif type_item == "Bassin":
                    pass
            # Modifie le nb de requêtes trouvé ci-dessus pour tenir compte des deux types de point
            if type_point == "Tous":
                nb_req += 1     # nb_req = nb_req * 2 quand l'API piézo tiendra compte des dept !
            elif type_point == "Piézomètre":      # condition à supprimer quand l'API piézo tiendra compte des dept !
                nb_req = 1
            # Fixe les bornes min et max du progressBar en fonction du nombre total de requêtes à envoyer
            self.dockwidget.progressBarStations.setRange(0, nb_req + 2)     # On ajoute 2 pour créer une étape de début et de fin de procédure
            num_iteration_progressbar = 1
            self.dockwidget.progressBarStations.setValue(num_iteration_progressbar)
            # Active le bouton d'interruption des calculs et désactive les boutons de téléchargement
            # des points et données pour éviter des déclenchements successifs intempestifs
            self.dockwidget.pb_annulerStations.setEnabled(True)
            self.dockwidget.pbt_telechargerPoints.setEnabled(False)
            self.dockwidget.pbt_telechargerData.setEnabled(False)
            # Création d'un sous-dossier horodaté pour contenir les résultats
            self.horodate = datetime.datetime.now().strftime('%y%m%d%H%M%S')
            self.chemin_sous_dossier_horodate = os.path.join(chemin_dossier_resultat, "Hubeau_" + self.horodate)
            self.chemin_geopackage = os.path.join(self.chemin_sous_dossier_horodate, "Stations_Hubeau.gpkg")
            os.mkdir(self.chemin_sous_dossier_horodate)

            # Pour les piézomètres, on ne fait pas de boucle sur les items de la listwidget
            # ni sur la liste de liste de départements et on envoie une seule requête à Hubeau
            # (moins de 5000 points pour la France et pas de filtre par département sur l'API Hubeau)
            if (type_point == "Piézomètre") or (type_point == "Tous"):
                # Contrôle de la demande d'interruption par l'utilisateur
                self.controler_interruption_utilisateur()
                # Peu importe les paramètres qui sont passés à la fonction car la requête PickEau les ignorera...
                nom_item = "Toute la France"
                list_dept = ["Tous"]
                # On lance la requête Hubeau
                df_req, statut_req = self.preq.requete_hubeau_par_dept(nom_item, list_dept, "stations_piezo_csv")
                # Si le résultat de la requête est correct on ajoute les données au df résultat
                if statut_req == 200:
                    df_station_piezo = df_req
                # Si le résultat est incorrect on lève une exception gérée et on avertit l'utilisateur
                else:
                    raise ErreurResultatRequeteIncorrect
                # Mise à jour du progressbar
                num_iteration_progressbar += 1
                self.dockwidget.progressBarStations.setValue(num_iteration_progressbar)
                # Si le df résultat contient des données
                if len(df_station_piezo) > 0:
                    # Suppression des doublons du df résultat et tri dans l'ordre des codes BSS
                    df_station_piezo = df_station_piezo.drop_duplicates()
                    df_station_piezo = df_station_piezo.sort_values('code_bss')     # En attendant de disposer de id_bss !
                    # TODO : sélection des points demandés par l'utilisateur quand l'API renverra un descriptif plus complet !
                    # Ecriture du df sous forme de csv dans le dossier défini par l'utilisateur
                    self.chemin_station_piezo = os.path.join(self.chemin_sous_dossier_horodate, "Stations_Piézomètres.csv")
                    self.pio.ecrire_fichier_csv(df_station_piezo, self.chemin_station_piezo)
                    # Lecture du fichier csv qui vient d'être écrit sur le disque et création d'une couche qgis sans ajout à la carte
                    self.couche_piezometre = self.lire_couche_csv(self.chemin_station_piezo, "Stations_Piézomètres", ";",
                                                                  champ_x="x", champ_y="y", epsg="EPSG:4326", ajouter_carte=False)
                    # Création d'un geopackage et ajout de la couche qgis avec reprojection dans la projection demandée par l'utilisateur
                    self.ecrire_couche_geopackage(self.chemin_geopackage, self.couche_piezometre, "Stations_Piézomètres", "EPSG:4326", epsg_reproj, ajouter_couche=False)
                else:
                    self.iface.messageBar().pushMessage(
                        "La requête vers Hubeau n'a renvoyé aucun résultat : " +
                        "il n'existe aucun piézomètre dans la sélection effectuée.",
                        Qgis.Warning)

            # Pour les qualitomètres on fait une boucle sur les items de la listwidget
            if (type_point == "Qualitomètre") or (type_point == "Tous"):
                # Création d'un df résultat vide
                df_station_qualite = pd.DataFrame()
                for item in dict_item.keys():
                    # Contrôle de la demande d'interruption par l'utilisateur
                    self.controler_interruption_utilisateur()
                    # Unpacking des éléments nécessaires pour envoyer la ou les requête(s)
                    type_item, nom_item, list_list_dept = dict_item[item]
                    # Boucle sur les listes de dept contenues dans list_list_dept :
                    # les requêtes s'effectuent de manière itérative par liste de départements
                    # (une liste de départements correspond au maximum à une ancienne région afin de limiter
                    # à moins de 20000 le nombre de résultats renvoyés par Hubeau tout en diminuant le nombre
                    # de requêtes successives à effectuer).
                    for list_dept in list_list_dept:
                        # Contrôle de la demande d'interruption par l'utilisateur
                        self.controler_interruption_utilisateur()
                        if type_item == "Administratif":
                            # On lance la requête Hubeau
                            df_req, statut_req = self.preq.requete_hubeau_par_dept(nom_item, list_dept, "stations_qualite_csv")
                            # Si le résultat de la requête est correct on ajoute les données au df résultat
                            if statut_req == 200:
                                if len(df_station_qualite) > 0:
                                    df_station_qualite = df_station_qualite.append(df_req)
                                else:
                                    df_station_qualite = df_req
                            # Si le résultat est incorrect on lève une exception gérée et on avertit l'utilisateur
                            else:
                                raise ErreurResultatRequeteIncorrect
                        # TODO : traiter les autres type_item
                        # Mise à jour du progressbar
                        num_iteration_progressbar += 1
                        self.dockwidget.progressBarStations.setValue(num_iteration_progressbar)
                # Si le df résultat contient des données
                if len(df_station_qualite) > 0:
                    # Suppression des doublons du df résultat et tri dans l'ordre des codes BSS
                    df_station_qualite = df_station_qualite.drop_duplicates()
                    df_station_qualite = df_station_qualite.sort_values('code_bss')     # En attendant de disposer de id_bss !
                    # TODO : sélection des points demandés par l'utilisateur
                    # Ecriture du df sous forme de csv dans le dossier défini par l'utilisateur
                    self.chemin_station_qualite = os.path.join(self.chemin_sous_dossier_horodate, "Stations_Qualitomètres.csv")
                    self.pio.ecrire_fichier_csv(df_station_qualite, self.chemin_station_qualite)
                    # Lecture du fichier csv qui vient d'être écrit sur le disque et création d'une couche qgis sans ajout à la carte
                    self.couche_qualitometre = self.lire_couche_csv(self.chemin_station_qualite, "Stations_Qualitomètres", ";",
                                                                    champ_x="longitude", champ_y="latitude", epsg="EPSG:4326", ajouter_carte=False)
                    # Si le geopackage existe
                    if os.path.isfile(self.chemin_geopackage):
                        # on ajoute la couche qgis au geopackage existant avec reprojection dans la projection demandée par l'utilisateur
                        self.ecrire_couche_geopackage(self.chemin_geopackage, self.couche_qualitometre, "Stations_Qualitomètres", "EPSG:4326", epsg_reproj, ajouter_couche=True)
                    else:
                        # Création d'un geopackage et ajout de la couche qgis avec reprojection dans la projection demandée par l'utilisateur
                        self.ecrire_couche_geopackage(self.chemin_geopackage, self.couche_qualitometre, "Stations_Qualitomètres", "EPSG:4326", epsg_reproj, ajouter_couche=False)
                else:
                    self.iface.messageBar().pushMessage(
                        "La requête vers Hubeau n'a renvoyé aucun résultat : " +
                        "il n'existe aucun qualitomètre dans la sélection effectuée.",
                        Qgis.Warning)

            # Instanciation de l'arborescence des groupes de couches via son noeud racine (root)
            self.root = QgsProject.instance().layerTreeRoot()
            # Création du groupe de couche associé à la requête, horodaté comme le sous-dossier résultat
            groupe_couches = self.root.insertGroup(0, "Hubeau_" + self.horodate)
            # Lecture du geopackage et ajout de toutes les couches dans un groupe de couches horodaté
            self.lire_toutes_couches_geopackage(self.chemin_geopackage, groupe_couches, developper_groupe=True)

            num_iteration_progressbar += 1
            self.dockwidget.progressBarStations.setValue(num_iteration_progressbar)
            self.iface.messageBar().pushMessage("Le téléchargement des points d'eau est terminé.")

        # Gestion des erreurs
        except ErreurListWidgetPointVide:
            self.iface.messageBar().pushMessage("La liste des points d'eau et groupes de points d'eau à télécharger est vide ! " +
                                                "le téléchargement des points d'eau n'a pas été effectué...",
                                                Qgis.Critical)
        except ErreurExistenceDossierResultat:
            self.iface.messageBar().pushMessage("Le chemin du dossier devant contenir les résultat n'existe pas : " +
                                                "le téléchargement des points d'eau n'a pas été effectué...",
                                                Qgis.Critical)
        except ErreurResultatRequeteIncorrect:
            self.iface.messageBar().pushMessage("Résultat incorrect de la requête " + item + " (" + str(statut_req) + ") : " +
                                                "le téléchargement des points d'eau est incomplet...",
                                                Qgis.Critical)
        except ErreurInterruptionUtilisateur:
            self.iface.messageBar().pushMessage("Opération interrompue par l'utilisateur : " +
                                                "le téléchargement des points d'eau est incomplet...",
                                                Qgis.Critical)
        except ErreurCreationSousDossierResultat:
            self.iface.messageBar().pushMessage("Impossible de créer le sous-dossier devant contenir les résultats : " +
                                                "le téléchargement des points d'eau n'a pas été effectué...",
                                                Qgis.Critical)
        except ErreurCreationCoucheQgis:
            self.iface.messageBar().pushMessage("La couche Qgis n'est pas valide et n'a pas été créée.",
                                                Qgis.Critical)
        except:
            self.iface.messageBar().pushMessage("Erreur inconnue : " +
                                               "le téléchargement des points d'eau n'a pas été effectué...",
                                                Qgis.Critical)

        # Fin systématique de la méthode, qu'il y ait une erreur ou non
        finally:
            self.dockwidget.progressBarStations.reset()
            self.dockwidget.pb_annulerStations.setEnabled(False)
            self.dockwidget.pbt_telechargerPoints.setEnabled(True)
            self.dockwidget.pbt_telechargerData.setEnabled(True)

    def choisir_groupe_parametre_pickeau(self, index):
        nom_groupe = self.dockwidget.cbx_choisirParametreGroupePickEau.itemText(index)
        if nom_groupe != "":
            self.dockwidget.cbx_choisirParametreGroupe1.setCurrentText("")
            self.dockwidget.cbx_choisirParametreGroupe2.clear()
            self.dockwidget.cbx_choisirParametreGroupe3.clear()
            self.dockwidget.cbx_choisirParametreGroupe4.clear()
            self.dockwidget.cbx_choisirParametre.clear()
            self.dockwidget.cbx_choisirParametre.addItems(self.pconfig.dict_groupe_pickeau_qualite[nom_groupe].keys())
        else:
            self.dockwidget.cbx_choisirParametre.clear()
            return None

    def choisir_groupe_parametre_1(self, index):
        """
        Peuple les listes déroulantes des groupes de paramètres Sandre de niveaux inférieur à 1
        et de la liste des paramètre associée au niveau de groupe le plus bas,
        en fonction du groupe de niveau 1 dont l'index est passé en paramètre.
        :param index: index du groupe Sandre de niveau 1
        :return: None
        """
        # Définition du groupe de paramètre Sandre de niveau 1
        nom_groupe_1 = self.dockwidget.cbx_choisirParametreGroupe1.itemText(index)
        self.dockwidget.cbx_choisirParametreGroupePickEau.setCurrentText("")
        # Définition des colonnes de la liste nationale des paramètres à filtrer
        if nom_groupe_1 == "Paramètres classés par classe":
            col_groupe_1 = "CLASSE_1"
            col_groupe_2 = "CLASSE_2"
            col_groupe_3 = "CLASSE_3"
            col_groupe_4 = "CLASSE_4"
        elif nom_groupe_1 == "Paramètres classés par usage":
            col_groupe_1 = "USAGE_1"
            col_groupe_2 = "USAGE_2"
            col_groupe_3 = "USAGE_3"
            col_groupe_4 = "USAGE_4"
        elif nom_groupe_1 == "Paramètres classés par textes réglementaires":
            col_groupe_1 = "REGLEMENT_1"
            col_groupe_2 = "REGLEMENT_2"
            col_groupe_3 = "REGLEMENT_3"
            col_groupe_4 = "REGLEMENT_4"
        elif nom_groupe_1 == "":
            self.dockwidget.cbx_choisirParametreGroupe2.clear()
            self.dockwidget.cbx_choisirParametreGroupe3.clear()
            self.dockwidget.cbx_choisirParametreGroupe4.clear()
            self.dockwidget.cbx_choisirParametre.clear()
            return None
        # Effacement des listes déroulantes des groupes de niveau inférieur à 1 et des paramètres
        self.dockwidget.cbx_choisirParametreGroupe2.clear()
        self.dockwidget.cbx_choisirParametreGroupe3.clear()
        self.dockwidget.cbx_choisirParametreGroupe4.clear()
        self.dockwidget.cbx_choisirParametre.clear()
        # Application de filtres sur les groupes de niveaux inférieurs à 1
        # pour peupler les listes déroulantes des groupes et des paramètres.
        # La fonction "extraire_liste_groupe" est utilisée pour régler le problème
        # des paramètres qui peuvent appartenir à plusieurs groupes de la même classe
        # (paramètres classés par usage ou par textes réglementaires)
        list_groupe_3 = []
        list_groupe_4 = []
        df_filtre = self.pconfig.df_lex_parametre[self.pconfig.df_lex_parametre[col_groupe_1].str.contains(nom_groupe_1, na=False, regex=False)]
        list_groupe_2 = self.extraire_liste_groupe(df_filtre[col_groupe_2])
        if len(list_groupe_2) > 0:
            df_filtre = df_filtre[df_filtre[col_groupe_2].str.contains(list_groupe_2[0], na=False, regex=False)]
            list_groupe_3 = self.extraire_liste_groupe(df_filtre[col_groupe_3])
            if len(list_groupe_3) > 0:
                df_filtre = df_filtre[df_filtre[col_groupe_3].str.contains(list_groupe_3[0], na=False, regex=False)]
                list_groupe_4 = self.extraire_liste_groupe(df_filtre[col_groupe_4])
                if len(list_groupe_4) > 0:
                    df_filtre = df_filtre[df_filtre[col_groupe_4].str.contains(list_groupe_4[0], na=False, regex=False)]
                else:
                    df_filtre = df_filtre[df_filtre[col_groupe_3].str.contains(list_groupe_3[0], na=False, regex=False)]
            else:
                df_filtre = df_filtre[df_filtre[col_groupe_2].str.contains(list_groupe_2[0], na=False, regex=False)]
        else:
            df_filtre = self.pconfig.df_lex_parametre[self.pconfig.df_lex_parametre[col_groupe_1].str.contains(nom_groupe_1, na=False, regex=False)]
        # Détermination de la liste des paramètres associée au filtre (nettoyée des espaces superflus et triée)
        list_parametre = df_filtre['NOM_LEXIQUE'].dropna().drop_duplicates().str.strip().sort_values().tolist()
        # Peuplement des listes déroulantes
        self.dockwidget.cbx_choisirParametreGroupe2.addItems(list_groupe_2)
        self.dockwidget.cbx_choisirParametreGroupe3.addItems(list_groupe_3)
        self.dockwidget.cbx_choisirParametreGroupe4.addItems(list_groupe_4)
        self.dockwidget.cbx_choisirParametre.addItems(list_parametre)

    def choisir_groupe_parametre_2(self, index):
        nom_groupe_1 = self.dockwidget.cbx_choisirParametreGroupe1.currentText()
        nom_groupe_2 = self.dockwidget.cbx_choisirParametreGroupe2.itemText(index)
        if nom_groupe_1 == "Paramètres classés par classe":
            col_groupe_1 = "CLASSE_1"
            col_groupe_2 = "CLASSE_2"
            col_groupe_3 = "CLASSE_3"
            col_groupe_4 = "CLASSE_4"
        elif nom_groupe_1 == "Paramètres classés par usage":
            col_groupe_1 = "USAGE_1"
            col_groupe_2 = "USAGE_2"
            col_groupe_3 = "USAGE_3"
            col_groupe_4 = "USAGE_4"
        elif nom_groupe_1 == "Paramètres classés par textes réglementaires":
            col_groupe_1 = "REGLEMENT_1"
            col_groupe_2 = "REGLEMENT_2"
            col_groupe_3 = "REGLEMENT_3"
            col_groupe_4 = "REGLEMENT_4"
        self.dockwidget.cbx_choisirParametreGroupe3.clear()
        self.dockwidget.cbx_choisirParametreGroupe4.clear()
        self.dockwidget.cbx_choisirParametre.clear()
        list_groupe_4 = []
        df_filtre = self.pconfig.df_lex_parametre[(self.pconfig.df_lex_parametre[col_groupe_1].str.contains(nom_groupe_1, na=False, regex=False))
                                                  & (self.pconfig.df_lex_parametre[col_groupe_2].str.contains(nom_groupe_2, na=False, regex=False))]
        list_groupe_3 = self.extraire_liste_groupe(df_filtre[col_groupe_3])
        # list_groupe_3 = df_filtre[col_groupe_3].dropna().drop_duplicates().sort_values().tolist()
        if len(list_groupe_3) > 0:
            df_filtre = df_filtre[df_filtre[col_groupe_3].str.contains(list_groupe_3[0], na=False, regex=False)]
            list_groupe_4 = self.extraire_liste_groupe(df_filtre[col_groupe_4])
            # list_groupe_4 = df_filtre[col_groupe_4].dropna().drop_duplicates().sort_values().tolist()
            if len(list_groupe_4) > 0:
                df_filtre = df_filtre[df_filtre[col_groupe_4].str.contains(list_groupe_4[0], na=False, regex=False)]
            else:
                df_filtre = df_filtre[df_filtre[col_groupe_3].str.contains(list_groupe_3[0], na=False, regex=False)]
        else:
            df_filtre = self.pconfig.df_lex_parametre[(self.pconfig.df_lex_parametre[col_groupe_1].str.contains(nom_groupe_1, na=False, regex=False))
                                                      & (self.pconfig.df_lex_parametre[col_groupe_2].str.contains(nom_groupe_2, na=False, regex=False))]
        list_parametre = df_filtre['NOM_LEXIQUE'].dropna().drop_duplicates().str.strip().sort_values().tolist()
        self.dockwidget.cbx_choisirParametreGroupe3.addItems(list_groupe_3)
        self.dockwidget.cbx_choisirParametreGroupe4.addItems(list_groupe_4)
        self.dockwidget.cbx_choisirParametre.addItems(list_parametre)

    def choisir_groupe_parametre_3(self, index):
        nom_groupe_1 = self.dockwidget.cbx_choisirParametreGroupe1.currentText()
        nom_groupe_2 = self.dockwidget.cbx_choisirParametreGroupe2.currentText()
        nom_groupe_3 = self.dockwidget.cbx_choisirParametreGroupe3.itemText(index)
        if nom_groupe_1 == "Paramètres classés par classe":
            col_groupe_1 = "CLASSE_1"
            col_groupe_2 = "CLASSE_2"
            col_groupe_3 = "CLASSE_3"
            col_groupe_4 = "CLASSE_4"
        elif nom_groupe_1 == "Paramètres classés par usage":
            col_groupe_1 = "USAGE_1"
            col_groupe_2 = "USAGE_2"
            col_groupe_3 = "USAGE_3"
            col_groupe_4 = "USAGE_4"
        elif nom_groupe_1 == "Paramètres classés par textes réglementaires":
            col_groupe_1 = "REGLEMENT_1"
            col_groupe_2 = "REGLEMENT_2"
            col_groupe_3 = "REGLEMENT_3"
            col_groupe_4 = "REGLEMENT_4"
        self.dockwidget.cbx_choisirParametreGroupe4.clear()
        self.dockwidget.cbx_choisirParametre.clear()
        df_filtre = self.pconfig.df_lex_parametre[(self.pconfig.df_lex_parametre[col_groupe_1].str.contains(nom_groupe_1, na=False, regex=False))
                                                & (self.pconfig.df_lex_parametre[col_groupe_2].str.contains(nom_groupe_2, na=False, regex=False))
                                                & (self.pconfig.df_lex_parametre[col_groupe_3].str.contains(nom_groupe_3, na=False, regex=False))]
        list_groupe_4 = self.extraire_liste_groupe(df_filtre[col_groupe_4])
        if len(list_groupe_4) > 0:
            df_filtre = df_filtre[df_filtre[col_groupe_4].str.contains(list_groupe_4[0], na=False, regex=False)]
        else:
            df_filtre = self.pconfig.df_lex_parametre[(self.pconfig.df_lex_parametre[col_groupe_1].str.contains(nom_groupe_1, na=False, regex=False))
                                                      & (self.pconfig.df_lex_parametre[col_groupe_2].str.contains(nom_groupe_2, na=False, regex=False))
                                                      & (self.pconfig.df_lex_parametre[col_groupe_3].str.contains(nom_groupe_3, na=False, regex=False))]
        list_parametre = df_filtre['NOM_LEXIQUE'].dropna().drop_duplicates().str.strip().sort_values().tolist()
        self.dockwidget.cbx_choisirParametreGroupe4.addItems(list_groupe_4)
        self.dockwidget.cbx_choisirParametre.addItems(list_parametre)

    def choisir_groupe_parametre_4(self, index):
        nom_groupe_1 = self.dockwidget.cbx_choisirParametreGroupe1.currentText()
        nom_groupe_2 = self.dockwidget.cbx_choisirParametreGroupe2.currentText()
        nom_groupe_3 = self.dockwidget.cbx_choisirParametreGroupe3.currentText()
        nom_groupe_4 = self.dockwidget.cbx_choisirParametreGroupe4.itemText(index)
        if nom_groupe_1 == "Paramètres classés par classe":
            col_groupe_1 = "CLASSE_1"
            col_groupe_2 = "CLASSE_2"
            col_groupe_3 = "CLASSE_3"
            col_groupe_4 = "CLASSE_4"
        elif nom_groupe_1 == "Paramètres classés par usage":
            col_groupe_1 = "USAGE_1"
            col_groupe_2 = "USAGE_2"
            col_groupe_3 = "USAGE_3"
            col_groupe_4 = "USAGE_4"
        elif nom_groupe_1 == "Paramètres classés par textes réglementaires":
            col_groupe_1 = "REGLEMENT_1"
            col_groupe_2 = "REGLEMENT_2"
            col_groupe_3 = "REGLEMENT_3"
            col_groupe_4 = "REGLEMENT_4"
        self.dockwidget.cbx_choisirParametre.clear()
        df_filtre = self.pconfig.df_lex_parametre[(self.pconfig.df_lex_parametre[col_groupe_1].str.contains(nom_groupe_1, na=False, regex=False))
                                                & (self.pconfig.df_lex_parametre[col_groupe_2].str.contains(nom_groupe_2, na=False, regex=False))
                                                & (self.pconfig.df_lex_parametre[col_groupe_3].str.contains(nom_groupe_3, na=False, regex=False))
                                                & (self.pconfig.df_lex_parametre[col_groupe_4].str.contains(nom_groupe_4, na=False, regex=False))]
        list_parametre = df_filtre['NOM_LEXIQUE'].dropna().drop_duplicates().str.strip().sort_values().tolist()
        self.dockwidget.cbx_choisirParametre.addItems(list_parametre)

    def ajouter_parametre_quantite(self):
        nom_item = self.dockwidget.cbx_choisirParametreQuantite.currentText()
        self.dockwidget.listw_afficherItemSelectionParametre.addItem("Paramètre Quantité - " + nom_item)

    def ajouter_parametre_groupe_pickeau(self):
        nom_item = self.dockwidget.cbx_choisirParametreGroupePickEau.currentText()
        self.dockwidget.listw_afficherItemSelectionParametre.addItem("Groupe Qualité PickEau - " + nom_item)

    def ajouter_parametre_groupe_1(self):
        nom_item = self.dockwidget.cbx_choisirParametreGroupe1.currentText()
        self.dockwidget.listw_afficherItemSelectionParametre.addItem("Groupe Qualité 1 - " + nom_item)

    def ajouter_parametre_groupe_2(self):
        nom_item = self.dockwidget.cbx_choisirParametreGroupe2.currentText()
        self.dockwidget.listw_afficherItemSelectionParametre.addItem("Groupe Qualité 2 - " + nom_item)

    def ajouter_parametre_groupe_3(self):
        nom_item = self.dockwidget.cbx_choisirParametreGroupe3.currentText()
        self.dockwidget.listw_afficherItemSelectionParametre.addItem("Groupe Qualité 3 - " + nom_item)

    def ajouter_parametre_groupe_4(self):
        nom_item = self.dockwidget.cbx_choisirParametreGroupe4.currentText()
        self.dockwidget.listw_afficherItemSelectionParametre.addItem("Groupe Qualité 4 - " + nom_item)

    def ajouter_parametre_parametre(self):
        nom_item = self.dockwidget.cbx_choisirParametre.currentText()
        self.dockwidget.listw_afficherItemSelectionParametre.addItem("Paramètre Qualité - " + nom_item)

    def ajouter_parametre_code_sandre(self):
        nom_item = self.dockwidget.le_saisirCodeSandre.text()
        self.dockwidget.listw_afficherItemSelectionParametre.addItem("Code Qualité Sandre - " + nom_item)

    def supprimer_parametre(self):
        index_item = self.dockwidget.listw_afficherItemSelectionParametre.currentRow()
        self.dockwidget.listw_afficherItemSelectionParametre.takeItem(index_item)

    def vider_list_parametre(self):
        self.dockwidget.listw_afficherItemSelectionParametre.clear()

    def telecharger_data(self):
        """
        Téléchargement des données Hubeau pour les points sélectionnés de la couche courante :
        le nom de la couche de points doit contenir "Piézomètre" ou "Qualitomètre" et
        ses attributs "code_bss", "x", "y" (piézomètre) ou "code_bss", "longitude", "latitude" (qualitomètre)
        doivent exister.
        :return:
        """

        telecharger_data_piezometre = False
        telecharger_data_qualitometre = False
        # Définition du flag d'interruption des boucles de requete par appui sur le bouton 'Interrompre'
        self.stop = False
        # L'ensemble de la fonction est inclus dans un bloc try de niveau le plus haut pour capturer
        # tous les types d'erreurs gérés (par "raise") : chaque erreur gérée rencontrée est remontée
        # jusqu'à ce niveau et passée au bloc "except" correspondant (voir en bas de la fonction).
        # Il est possible d'insérer des structures try - except de niveau inférieur, chaque except de niveau
        # inférieur devant lever par "raise" une exception gérée qui remontera jusqu'au niveau supérieur.
        try:

            # Détermination du nom et des attributs des points sélectionnés de la couche courante
            try:
                couche_courante = self.iface.activeLayer()
            except:
                raise ErreurAucuneCoucheSelectionnee
                
            # COMMENTED BY Benjamin GRENARD
            if ("Piézomètre" in couche_courante.name()):
                print("never goes there")
                # list_tup_piezometre = self.obtenir_liste_attribut_point_selectionne(couche_courante, ["code_bss", "x", "y"])
                # if len(list_tup_piezometre) > 0:
                #     list_tup_piezometre = list(set(list_tup_piezometre))  # élimination des doublons éventuels
                #     telecharger_data_piezometre = True
                # else:
                #     raise ErreurAucuneStationSelectionnee
            elif ("Qualitomètre" in couche_courante.name()):
                list_tup_qualitometre = self.obtenir_liste_attribut_point_selectionne(couche_courante, ["code_bss", "longitude", "latitude"])
                if len(list_tup_qualitometre) > 0:
                    list_tup_qualitometre = list(set(list_tup_qualitometre)) # élimination des doublons éventuels
                    telecharger_data_qualitometre = True
                else:
                    raise ErreurAucuneStationSelectionnee
            else:
                raise ErreurCoucheQgisNonConforme

            # Détermination du chemin du geopackage auquel appartient la couche courante
            chemin_fichier_geopackage = couche_courante.source().split("|")[0]
            if not os.path.isfile(chemin_fichier_geopackage):
                raise ErreurExistenceFichierGeopackage

            # Détermination du chemin du dossier contenant le geopackage auquel appartient la couche courante
            chemin_dossier_geopackage = os.path.dirname(chemin_fichier_geopackage)
            if not os.path.isdir(chemin_dossier_geopackage):
                raise ErreurExistenceDossierGeopackage

            # Traitement des informations écrites par l'utilisateur dans la listwidget
            list_item = self.obtenir_liste_item_listwidget(self.dockwidget.listw_afficherItemSelectionParametre)
            # Vérification de la présence d'items dans la liste --> si vide = erreur
            if len(list_item) == 0:
                raise ErreurListWidgetParametreVide
            # Renvoie le crs sélectionné par l'utilisateur (objet)
            crs_reproj = self.dockwidget.qgs_projection.crs()
            # Renvoie le crs (p.ex sous la forme "EPSG:2154")
            epsg_reproj = crs_reproj.authid()
            # # On en extrait le code epsg et on le convertit en entier
            # code_epsg_reproj = int(crs_reproj.authid()[5:])
            # Elimination des doublons de la liste
            list_item = list(set(list_item))
            # Boucle de remplissage des listes nécessaires pour construire les requêtes
            nb_req = 0
            list_code_parametre_quantite = []
            list_code_parametre_qualite = []
            list_code_groupe_qualite = []
            list_code_parametre_groupe_qualite = []
            for item in list_item:
                # Traitement du texte de chaque item pour obtenir le type et le nom d'item
                type_item = item.split(" - ")[0]
                nom_item = item.split(" - ")[1]
                if type_item == "Paramètre Quantité":
                    list_code_parametre_quantite.append(nom_item)
                elif type_item == "Groupe Qualité PickEau":
                    list_code_parametre_qualite += list(self.pconfig.dict_groupe_pickeau_qualite[nom_item].values()) # le dict renvoie un dict de str
                elif (type_item == "Groupe Qualité 1") or (type_item == "Groupe Qualité 2") or (type_item == "Groupe Qualité 3") or (type_item == "Groupe Qualité 4"):
                    list_code_groupe_qualite.append(self.pconfig.dict_groupe_code_qualite[nom_item]) # le dict renvoie une str
                    list_code_parametre_groupe_qualite += self.pconfig.dict_groupe_parametre_qualite[nom_item] # le dict renvoie une liste de str
                elif type_item == "Paramètre Qualité":
                    code_parametre_qualite = nom_item.split(" | ")[1]
                    list_code_parametre_qualite.append(code_parametre_qualite)
                # TODO : traiter les autres type_item
                elif type_item == "Code Qualité Sandre":
                    pass

            # Elimination des doublons dans les listes de groupes et de paramètres à passer à la requête
            list_code_parametre_quantite = list(set(list_code_parametre_quantite))
            list_code_parametre_qualite = list(set(list_code_parametre_qualite))
            list_code_groupe_qualite = list(set(list_code_groupe_qualite))

            # Elimination des paramètres déjà inclus dans un groupe
            list_code_parametre_groupe_qualite = list(set(list_code_parametre_groupe_qualite))
            list_code_parametre_qualite = list(set(list_code_parametre_qualite) - set(list_code_parametre_groupe_qualite))

            if len(list_code_parametre_qualite) > 200:
                raise ErreurNombreParametreQualiteTropGrand
            if len(list_code_groupe_qualite) > 200:
                raise ErreurNombreGroupeQualiteTropGrand

            # Calcul du nombre de requêtes total
            if telecharger_data_piezometre == True:
                if len(list_code_parametre_quantite) > 0:
                    nb_req = len(list_tup_piezometre) * len(list_code_parametre_quantite)
                else:
                    raise ErreurListeParametreQuantiteIncorrecte
            elif telecharger_data_qualitometre == True:
                if (len(list_code_groupe_qualite) > 0) or (len(list_code_parametre_qualite) > 0):
                    nb_req = len(list_tup_qualitometre) * (len(list_code_groupe_qualite) + 1) # ajout de 1 pour les codes paramètre passés en une fois (limitation à 200)
                else:
                    raise ErreurListeParametreQualiteIncorrecte

            # Fixe les bornes min et max du progressBar en fonction du nombre total de requêtes à envoyer
            self.dockwidget.progressBar.setRange(0, nb_req + 2)     # On ajoute 2 pour créer une étape de début et de fin de procédure
            num_iteration_progressbar = 1
            self.dockwidget.progressBar.setValue(num_iteration_progressbar)
            # Active le bouton d'interruption des calculs et désactive les boutons de téléchargement
            # des points et données pour éviter des déclenchements successifs intempestifs
            self.dockwidget.pb_annuler.setEnabled(True)
            self.dockwidget.pbt_telechargerPoints.setEnabled(False)
            self.dockwidget.pbt_telechargerData.setEnabled(False)

            # if telecharger_data_piezometre == True:
            #     # Boucle sur les piézomètres sélectionnés
            #     df_data_piezo = pd.DataFrame()
            #     for code_bss, coord_x, coord_y in list_tup_piezometre:
            #         self.controler_interruption_utilisateur()
            #         # Boucle sur les paramètres demandés (uniquement piézo pour l'instant !)
            #         for code_parametre in list_code_parametre_quantite:
            #             self.controler_interruption_utilisateur()
            #             # On lance la requête Hubeau
            #             df_req, statut_req = self.preq.requete_hubeau_par_point(code_bss, [], [code_parametre], "chroniques_piezo_csv")
            #             # Si le résultat de la requête est correct on ajoute les données au df résultat
            #             if statut_req == 200:
            #                 df_req["x_wgs84"] = coord_x
            #                 df_req["y_wgs84"] = coord_y
            #                 if len(df_data_piezo) > 0:
            #                     df_data_piezo = df_data_piezo.append(df_req)
            #                 else:
            #                     df_data_piezo = df_req
            #             # Si le résultat est incorrect on lève une exception gérée et on avertit l'utilisateur
            #             else:
            #                 raise ErreurResultatRequeteIncorrect
            #             # Mise à jour du progressbar
            #             num_iteration_progressbar += 1
            #             self.dockwidget.progressBar.setValue(num_iteration_progressbar)

            #     # Si le df résultat pour les chroniques piézométriques contient des données
            #     if len(df_data_piezo) > 0:

            #         # Suppression des doublons du df résultat (doublons ADES) et tri
            #         df_data_piezo = df_data_piezo.drop_duplicates()
            #         df_data_piezo = df_data_piezo.sort_values(['code_bss', 'date_mesure'])     # En attendant de disposer de id_bss !

            #         # Création du sous-dossier qui contiendra les résultats d'analyse et le geopackage des points correspondantes
            #         nb_point = str(df_data_piezo['code_bss'].unique().shape[0])
            #         horodate_resultat = datetime.datetime.now().strftime('%y%m%d%H%M%S')
            #         nom_dossier_resultat = f"Résultats_Piézométrie_{nb_point}_points_{horodate_resultat}"
            #         chemin_dossier_resultat = os.path.join(chemin_dossier_geopackage, nom_dossier_resultat)
            #         os.mkdir(chemin_dossier_resultat)
            #         chemin_geopackage_resultat = os.path.join(chemin_dossier_resultat, nom_dossier_resultat + '.gpkg')

            #         # Création du groupe qui contiendra les couches de points par paramètre
            #         groupe_parent_couche_courante = self.iface.layerTreeView().currentGroupNode()
            #         groupe_couche = groupe_parent_couche_courante.addGroup(nom_dossier_resultat)

            #         # Création du df des métadonnées des points d'eau et écriture d'un csv temporaire
            #         df_infos = df_data_piezo[self.preq.list_col_metadata_niveaux_nappes_chroniques_csv +
            #                                  ['x_wgs84', 'y_wgs84']]
            #         df_infos['code_param'] = ''
            #         df_infos['nom_param'] = 'Niveaux_Piézométriques'
            #         df_infos = df_infos.drop_duplicates()
            #         chemin_csv_temp = os.path.join(chemin_dossier_resultat, "Temp.csv")
            #         self.pio.ecrire_fichier_csv(df_infos, chemin_csv_temp)

            #         # Lecture du fichier csv temporaire qui vient d'être écrit sur le disque et création d'une couche qgis temporaire sans ajout à la carte
            #         couche_infos = self.lire_couche_csv(chemin_csv_temp, "Couche_Temporaire", ";",
            #                                             champ_x="x_wgs84", champ_y="y_wgs84", epsg="EPSG:4326", ajouter_carte=False)

            #         # Ecriture de la couche qgis en mémoire dans un nouveau geopackage avec reprojection dans la projection demandée par l'utilisateur
            #         self.ecrire_couche_geopackage(chemin_geopackage_resultat, couche_infos, "Points_Niveaux_Piézométriques", "EPSG:4326", epsg_reproj, ajouter_couche=False)

            #         # Lecture du geopackage et ajout de la nouvelle couche dans le nouveau groupe de couches des résultats
            #         self.lire_couche_geopackage(chemin_geopackage_resultat, "Points_Niveaux_Piézométriques", groupe_couche, developper_groupe=False)

            #         # Création du df des niveaux piézométriques et écriture au format csv
            #         df_resultat = df_data_piezo[['code_bss'] + self.preq.list_col_data_niveaux_nappes_chroniques_csv]
            #         df_resultat['commentaire'] = 'Correct'  # Ajout d'un champ commentaire pour que l'utilisateur puisse commenter chaque analyse
            #         nom_csv_resultat = f"Données_Niveaux_{horodate_resultat}.csv"
            #         chemin_csv_resultat = os.path.join(chemin_dossier_resultat, nom_csv_resultat)
            #         self.pio.ecrire_fichier_csv(df_resultat, chemin_csv_resultat)

            #         # Lecture du fichier csv des niveaux piézométriques qui vient d'être écrit sur le disque et création d'une couche qgis temporaire sans ajout à la carte
            #         couche_donnees_niveaux = self.lire_couche_csv(chemin_csv_resultat, "Couche_Temporaire_Data_Niveaux", ";", ajouter_carte=False)

            #         # Ajout de la couche des analyses chimiques dans le geopackage déjà existant
            #         self.ecrire_couche_geopackage(chemin_geopackage_resultat, couche_donnees_niveaux, nom_csv_resultat, ajouter_couche=True)

            #         # Lecture du geopackage et ajout de la nouvelle couche des analyses chimiques dans le nouveau groupe de couches des résultats
            #         self.lire_couche_geopackage(chemin_geopackage_resultat, nom_csv_resultat, groupe_couche, developper_groupe=False)

            #     else:
            #         self.iface.messageBar().pushMessage(
            #             "La requête vers Hubeau n'a renvoyé aucun résultat : " +
            #             "il n'existe aucune chronique piézométrique correspondant à la sélection de points effectuée.",
            #             Qgis.Warning)

            if telecharger_data_qualitometre == True:

                # Boucle sur les qualitomètres sélectionnés
                df_data_qualite = pd.DataFrame()
                for code_bss, coord_x, coord_y in list_tup_qualitometre:
                    self.controler_interruption_utilisateur()

                    # Boucle sur les groupes de paramètres demandés
                    for code_groupe in list_code_groupe_qualite:
                        self.controler_interruption_utilisateur()
                        # On lance la requête Hubeau
                        df_req, statut_req = self.preq.requete_hubeau_par_point(code_bss, [code_groupe], [], "analyses_qualite_csv")
                        # Si le résultat de la requête est correct on ajoute les données au df résultat
                        if statut_req == 200:
                            df_req["x_wgs84"] = coord_x
                            df_req["y_wgs84"] = coord_y
                            if len(df_data_qualite) > 0:
                                df_data_qualite = df_data_qualite.append(df_req)
                            else:
                                df_data_qualite = df_req
                        # Si le résultat est incorrect on lève une exception gérée et on avertit l'utilisateur
                        else:
                            raise ErreurResultatRequeteIncorrect
                        # Mise à jour du progressbar
                        num_iteration_progressbar += 1
                        self.dockwidget.progressBar.setValue(num_iteration_progressbar)

                    # Requête supplémentaire pour les paramètres qualité demandés individuellement (max 200)
                    if len(list_code_parametre_qualite) > 0:
                        self.controler_interruption_utilisateur()
                        # On lance la requête Hubeau
                        df_req, statut_req = self.preq.requete_hubeau_par_point(code_bss, [], list_code_parametre_qualite, "analyses_qualite_csv")
                        # Si le résultat de la requête est correct on ajoute les données au df résultat
                        if statut_req == 200:
                            df_req["x_wgs84"] = coord_x
                            df_req["y_wgs84"] = coord_y
                            if len(df_data_qualite) > 0:
                                df_data_qualite = df_data_qualite.append(df_req)
                            else:
                                df_data_qualite = df_req
                        # Si le résultat est incorrect on lève une exception gérée et on avertit l'utilisateur
                        else:
                            raise ErreurResultatRequeteIncorrect

                    # Mise à jour du progressbar
                    num_iteration_progressbar += 1
                    self.dockwidget.progressBar.setValue(num_iteration_progressbar)

                # Si le df résultat pour les analyses qualité contient des données
                if len(df_data_qualite) > 0:

                    # Suppression des doublons du df résultat (doublons ADES) et tri
                    df_data_qualite = df_data_qualite.drop_duplicates()
                    df_data_qualite = df_data_qualite.sort_values(['code_bss', 'nom_param', 'date_debut_prelevement'])     # En attendant de disposer de id_bss !

                    # Création du sous-dossier qui contiendra les résultats d'analyse et le geopackage des points
                    nb_point = str(df_data_qualite['code_bss'].unique().shape[0])
                    nb_param = str(df_data_qualite['nom_param'].unique().shape[0])
                    horodate_resultat = datetime.datetime.now().strftime('%y%m%d%H%M%S')
                    nom_dossier_resultat = f"Résultats_Qualité_{nb_point}_points_{nb_param}_parametres_{horodate_resultat}"
                    chemin_dossier_resultat = os.path.join(chemin_dossier_geopackage, nom_dossier_resultat)
                    os.mkdir(chemin_dossier_resultat)
                    chemin_geopackage_resultat = os.path.join(chemin_dossier_resultat, nom_dossier_resultat + '.gpkg')

                    # Création du groupe qui contiendra les couches de points par paramètre
                    groupe_parent_couche_courante = self.iface.layerTreeView().currentGroupNode()
                    groupe_couche = groupe_parent_couche_courante.addGroup(nom_dossier_resultat)

                    # Itération sur les paramètres pour créer autant de couches qu'il y a de paramètres
                    df_resultat = pd.DataFrame()
                    grp_data_qualite = df_data_qualite.groupby(by=['nom_param'])
                    for nom_param, df_grp in grp_data_qualite:

                        code_param = str(int(df_grp['code_param'].tolist()[0]))
                        nom_couche = f"{nom_param}_{code_param}"

                        # Ajout des données du paramètre au df résultat
                        df_resultat = df_resultat.append(df_grp[['code_bss'] + self.preq.list_col_data_qualite_nappes_analyses_csv])

                        # Création du df des métadonnées des points d'eau et écriture d'un csv temporaire
                        df_infos_grp = df_grp[self.preq.list_col_metadata_qualite_nappes_analyses_csv +
                                              ['code_param', 'nom_param', 'x_wgs84', 'y_wgs84']]
                        df_infos_grp = df_infos_grp.drop_duplicates()
                        chemin_csv_temp = os.path.join(chemin_dossier_resultat, "Temp.csv")
                        self.pio.ecrire_fichier_csv(df_infos_grp, chemin_csv_temp)

                        # Lecture du fichier csv temporaire des points qui vient d'être écrit sur le disque et création d'une couche qgis temporaire sans ajout à la carte
                        couche_points_analyses = self.lire_couche_csv(chemin_csv_temp, "Couche_Temporaire", ";",
                                                                      champ_x="x_wgs84", champ_y="y_wgs84", epsg="EPSG:4326", ajouter_carte=False)

                        # Ajout de la couche qgis en mémoire à un geopackage avec reprojection dans la projection demandée par l'utilisateur
                        if os.path.isfile(chemin_geopackage_resultat):
                            # Ajout de la couche si le geopackage existe déjà
                            self.ecrire_couche_geopackage(chemin_geopackage_resultat, couche_points_analyses, f"Points_{nom_couche}", "EPSG:4326", epsg_reproj, ajouter_couche=True)
                        else:
                            # Sinon création d'un geopackage et ajout de la couche
                            self.ecrire_couche_geopackage(chemin_geopackage_resultat, couche_points_analyses, f"Points_{nom_couche}", "EPSG:4326", epsg_reproj, ajouter_couche=False)

                        # Lecture du geopackage et ajout de la nouvelle couche dans le nouveau groupe de couches des résultats
                        self.lire_couche_geopackage(chemin_geopackage_resultat, f"Points_{nom_couche}", groupe_couche, developper_groupe=False)

                    # Ecriture du csv des analyses chimiques
                    nom_csv_resultat = f"Données_Analyses_{horodate_resultat}.csv"
                    chemin_csv_resultat = os.path.join(chemin_dossier_resultat, nom_csv_resultat)
                    df_resultat['commentaire'] = 'Correct'  # Ajout d'un champ commentaire pour que l'utilisateur puisse commenter chaque analyse
                    self.pio.ecrire_fichier_csv(df_resultat, chemin_csv_resultat)

                    # Lecture du fichier csv des analyses chimiques qui vient d'être écrit sur le disque et création d'une couche qgis temporaire sans ajout à la carte
                    couche_donnees_analyses = self.lire_couche_csv(chemin_csv_resultat, "Couche_Temporaire_Data_Analyses", ";", ajouter_carte=False)

                    # Ajout de la couche des analyses chimiques dans le geopackage déjà existant
                    self.ecrire_couche_geopackage(chemin_geopackage_resultat, couche_donnees_analyses, nom_csv_resultat, ajouter_couche=True)

                    # Lecture du geopackage et ajout de la nouvelle couche des analyses chimiques dans le nouveau groupe de couches des résultats
                    self.lire_couche_geopackage(chemin_geopackage_resultat, nom_csv_resultat, groupe_couche, developper_groupe=False)

                else:
                    self.iface.messageBar().pushMessage(
                        "La requête vers Hubeau n'a renvoyé aucun résultat : " +
                        "il n'existe aucune analyse chimique correspondant à la sélection de points effectuée.",
                        Qgis.Warning)

            num_iteration_progressbar += 1
            self.dockwidget.progressBar.setValue(num_iteration_progressbar)
            self.iface.messageBar().pushMessage("Le téléchargement des données est terminé.")
            # os.remove(chemin_csv_infos)

        # Gestion des erreurs
        except ErreurAucuneCoucheSelectionnee:
            self.iface.messageBar().pushMessage("Aucune couche Qgis de stations Hubeau n'est active ! " +
                                                "Veuillez activer une couche de stations Hubeau et sélectionner au moins une station...",
                                                Qgis.Critical)
        except ErreurAucuneStationSelectionnee:
            self.iface.messageBar().pushMessage("Aucune station de la couche active de stations Hubeau n'est sélectionnée ! " +
                                                "Veuillez sélectionner au moins une station...",
                                                Qgis.Critical)
        except ErreurCoucheQgisNonConforme:
            self.iface.messageBar().pushMessage("La couche Qgis active n'est pas une couche de stations Hubeau ! " +
                                                "Veuillez activer une couche de stations Hubeau et sélectionner au moins une station...",
                                                Qgis.Critical)
        except ErreurExistenceDossierGeopackage:
            self.iface.messageBar().pushMessage("Le dossier du geopackage contenant la couche de stations Hubeau activée n'existe pas : " +
                                                "le téléchargement des données n'a pas été effectué...",
                                                Qgis.Critical)
        except ErreurExistenceFichierGeopackage:
            self.iface.messageBar().pushMessage("Le fichier geopackage contenant la couche de stations Hubeau activée n'existe pas : " +
                                                "le téléchargement des données n'a pas été effectué...",
                                                Qgis.Critical)
        except ErreurListWidgetParametreVide:
            self.iface.messageBar().pushMessage("La liste des paramètres et groupes de paramètres à télécharger est vide ! " +
                                                "Le téléchargement des données n'a pas été effectué...",
                                                Qgis.Critical)
        except ErreurNombreGroupeQualiteTropGrand:
            self.iface.messageBar().pushMessage("Hubeau n'accepte pas le téléchargement de plus de 200 groupes de paramètres qualité : " +
                                                "le téléchargement des données n'a pas été effectué...",
                                                Qgis.Critical)
        except ErreurNombreParametreQualiteTropGrand:
            self.iface.messageBar().pushMessage("Hubeau n'accepte pas le téléchargement de plus de 200 paramètres qualité : " +
                                                "le téléchargement des données n'a pas été effectué...",
                                                Qgis.Critical)
        except ErreurListeParametreQuantiteIncorrecte:
            self.iface.messageBar().pushMessage("Aucun paramètre quantité n'est sélectionné ! " +
                                                "Le téléchargement des données n'a pas été effectué...",
                                                Qgis.Critical)
        except ErreurListeParametreQualiteIncorrecte:
            self.iface.messageBar().pushMessage("Aucun paramètre ou groupe de paramètre qualité n'est sélectionné ! " +
                                                "Le téléchargement des données n'a pas été effectué...",
                                                Qgis.Critical)
        except ErreurResultatRequeteIncorrect:
            self.iface.messageBar().pushMessage("Résultat incorrect de la requête : " +
                                                "le téléchargement des données est incomplet...",
                                                Qgis.Critical)
        except ErreurCreationCoucheQgis:
            self.iface.messageBar().pushMessage("La couche Qgis n'est pas valide et n'a pas été créée.",
                                                Qgis.Critical)
        except ErreurInterruptionUtilisateur:
            self.iface.messageBar().pushMessage("Opération interrompue par l'utilisateur : " +
                                                "le téléchargement des données est incomplet...",
                                                Qgis.Critical)
        except:
            self.iface.messageBar().pushMessage("Erreur inconnue : " +
                                                "le téléchargement des données est probablement incomplet ou n'a pas été effectué...",
                                                Qgis.Critical)

        # Fin systématique de la méthode, qu'il y ait une erreur ou non
        finally:
            self.dockwidget.progressBar.reset()
            self.dockwidget.pb_annuler.setEnabled(False)
            self.dockwidget.pbt_telechargerPoints.setEnabled(True)
            self.dockwidget.pbt_telechargerData.setEnabled(True)

    def obtenir_liste_item_listwidget(self, listwidget):
        list_item = []
        for i in range(listwidget.count()):
            list_item.append(listwidget.item(i).text())
        return list_item

    def stop_iteration(self):
        # Flag d'interruption de la boucle par appui sur le bouton 'Interrompre'
        self.stop = True

    def controler_interruption_utilisateur(self):
        # Traitement des événements pour permettre l'interruption par l'utilisateur
        QCoreApplication.processEvents()
        # Flag d'interruption de la boucle par appui sur le bouton 'Interrompre'
        if (self.stop is True):
            self.stop = False
            self.dockwidget.progressBar.reset()
            self.dockwidget.pb_annuler.setEnabled(False)
            raise ErreurInterruptionUtilisateur

    def lire_couche_csv(self, chemin_csv, nom_couche_qgis, separateur, champ_x='', champ_y='', epsg='', ajouter_carte=True):
        """
        Lit un csv et crée une couche Qgis.
        :param chemin_csv: (str) chemin du csv à lire
        :param nom_couche_qgis: (str) nom de la couche Qgis à créer
        :param separateur: (str) séparateur des champs du csv
        :param coord_x: (str) nom du champ de coordonnée x des points à créer
        :param coord_y: (str) nom du champ coordonnée y des points à créer
        :param epsg: (str) code epsg des coordonnées au format du type "EPSG:2154"
        :param ajouter_carte:
        :return: (QgsVectorLayer) couche Qgis
        """
        # Création de l'uri pour lire le csv
        # => Cas où on ne veut pas créer les points (notamment si les coordonnées n'existent pas)
        if (champ_x == '') or (champ_y == '') or (epsg == ''):
            uri = "file:///" + quote(chemin_csv)  # remplace les caractères non ascii du chemin
            uri += "?type=csv"
            uri += "&delimiter=" + separateur
            uri += "&detectTypes=yes"
            uri += "&subsetIndex=no"
            uri += "&watchFile=no"
        # Cas où on veut créer les points
        else:
            uri = "file:///" + quote(chemin_csv)  # remplace les caractères non ascii du chemin
            uri += "?type=csv"
            uri += "&delimiter=" + separateur
            uri += "&detectTypes=yes"
            uri += "&xField=" + champ_x
            uri += "&yField=" + champ_y
            uri += "&crs=" + epsg
            uri += "&spatialIndex=no"
            uri += "&subsetIndex=no"
            uri += "&watchFile=no"
        # Lecture du csv et création de la couche
        layer = QgsVectorLayer(uri, nom_couche_qgis, "delimitedtext")
        if not layer.isValid():
            raise ErreurCreationCoucheQgis
        # Ajout de la couche à la carte
        if ajouter_carte == True:
            QgsProject.instance().addMapLayers([layer])
        return layer

    def ecrire_couche_geopackage(self, chemin_geopackage, qgs_vector_layer, layer_name, epsg_origine="", epsg_destination="", ajouter_couche=False):
        """
        Ecrit une couche Qgis dans un geopackage existant ou à créer.
        :param chemin_geopackage: (str) chemin du geopackage existant ou à créer
        :param qgs_vector_layer: (QgsVectorLayer) objet couche vecteur à écrire dans le geopackage
        :param layer_name: (str) nom de la couche vecteur à écrire dans le geopackage
        :param epsg_origine="": (str) code epsg d'origine de la couche vecteur au format du type "EPSG:2154"
        :param epsg_destination="": (str) code epsg de reprojection de la couche vecteur au format du type "EPSG:2154"
        :param ajouter_couche=False: (bool) indique s'il faut ajouter la couche à un geopackage existant (True) ou créer le geopackage (False)
        :return: None
        """
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = layer_name
        options.fileEncoding = "utf-8"
        if (epsg_origine != "") and (epsg_destination != ""):
            transform_proj = QgsCoordinateTransform(QgsCoordinateReferenceSystem(epsg_origine),
                                                    QgsCoordinateReferenceSystem(epsg_destination),
                                                    QgsProject.instance())
            options.ct = transform_proj
        if ajouter_couche == True:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        QgsVectorFileWriter.writeAsVectorFormat(qgs_vector_layer, chemin_geopackage, options)

    def lire_couche_geopackage(self, chemin_geopackage, nom_couche, qgs_layer_tree_group, developper_groupe=False):
        """
        Lecture d'un geopackage et ajout d'une couche dans un groupe de couches.
        :param chemin_geopackage: (str) chemin du geopackage existant ou à créer
        :param nom_couche: (str) nom de la couche à lire dans le geopackage
        :param qgs_layer_tree_group: (QgsLayerTreeGroup) noeud de type groupe de l'arbre des noeuds (QgsLayerTree)
        :param developper_groupe: (bool) indique si le groupe doit être développé (True) ou non (False)
        :return: None
        """
        gpkg = ogr.Open(chemin_geopackage)
        gpkg_layer = QgsVectorLayer(chemin_geopackage + "|layername=" + nom_couche, nom_couche, 'ogr')
        if not gpkg_layer.isValid():
            raise ErreurCreationCoucheQgis
        QgsProject.instance().addMapLayer(gpkg_layer, False)
        layer_node = qgs_layer_tree_group.addLayer(gpkg_layer)
        if developper_groupe == True:
            layer_node.setExpanded(True)
        else:
            layer_node.setExpanded(False)

    def lire_toutes_couches_geopackage(self, chemin_geopackage, qgs_layer_tree_group, developper_groupe=False):
        """
        Lecture d'un geopackage et ajout de toutes les couches dans un groupe de couches.
        :param chemin_geopackage: (str) chemin du geopackage existant ou à créer
        :param qgs_layer_tree_group: (QgsLayerTreeGroup) noeud de type groupe de l'arbre des noeuds (QgsLayerTree)
        :param developper_groupe: (bool) indique si le groupe doit être développé (True) ou non (False)
        :return: None
        """
        gpkg = ogr.Open(chemin_geopackage)
        for layer in gpkg:
            gpkg_layer = QgsVectorLayer(chemin_geopackage + "|layername=" + layer.GetName(), layer.GetName(), 'ogr')
            if not gpkg_layer.isValid():
                raise ErreurCreationCoucheQgis
            QgsProject.instance().addMapLayer(gpkg_layer, False)
            layer_node = qgs_layer_tree_group.addLayer(gpkg_layer)
            if developper_groupe == True:
                layer_node.setExpanded(True)
            else:
                layer_node.setExpanded(False)

    def extraire_liste_groupe(self, serie):
        """
        Extrait une liste triée de groupes d'une Series pouvant contenir des groupes multiples
        (niveaux 3 et 4 du Sandre de ln_parametres) : les groupes multiples pour un même niveau
        et un même paramètre sont séparés par ';' et doivent être splittés.
        :param serie: objet Series
        :return: liste python triée
        """
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

    def obtenir_liste_attribut_point_selectionne(self, obj_layer, list_nom_attribut):
        """
        Fonction qui extrait pour chaque point sélectionné de la couche courante
        un tuple des valeurs des attributs dont la liste des noms est passée en paramètre.
        :return: liste de tuples
        """
        list_tup_valeur_attribut = []
        try:
            for selected_points in obj_layer.getSelectedFeatures():
                list_valeur_attribut = []
                for nom_attribut in list_nom_attribut:
                    list_valeur_attribut.append(selected_points[nom_attribut])
                list_tup_valeur_attribut.append(tuple(list_valeur_attribut))
        except:
            return []
        return list_tup_valeur_attribut

    def telecharger_data_piezometre(self):
        """
        Lancement du téléchargement des donnees piezometrique et gestion des messages d'erreurs
        """
        # Gestion de la progress bar
        self.stop = False
        self.dockwidget.pbt_telechargerData_pizo.setEnabled(True)
        num_iteration_progressbar = 1  # une seule requete pour hubeau
        nb_req = num_iteration_progressbar + 2  # une seule requete pour hubeau ajoute 2 pour les etapes d ajouts
        self.dockwidget.progressBar.setRange(0, nb_req)

        # Vérifier sélection
        couche_courante = self.iface.activeLayer()
        if (couche_courante):
            if ("Piézomètre" in couche_courante.name()):
                list_tup_piezometre = self.obtenir_liste_attribut_point_selectionne(couche_courante, ["code_bss", "x", "y"])
                if len(list_tup_piezometre) > 0:
                    list_tup_piezometre = list(set(list_tup_piezometre))  # élimination des doublons éventuels
                    self.lancer_telecharger_data_piezometre(list_tup_piezometre, couche_courante, num_iteration_progressbar, nb_req)
                else:
                    self.iface.messageBar().pushWarning("Aucune station sélectionnée.", "Téléchargement impossible")
            else:
                self.iface.messageBar().pushWarning("Sélectionner une couche Stations Piézomètres.", "Téléchargement impossible")
        else:
            self.iface.messageBar().pushWarning("Aucune couche sélectionnée. Sélectionner une couche Stations Piézomètres.", "Téléchargement impossible")

    def lancer_telecharger_data_piezometre(self, list_tup_piezometre: list,
                                           couche_courante: QgsVectorLayer,
                                           num_iteration_progressbar: int,
                                           nb_req: int):
        """
        Téléchargement des données et ajout à la carte

        :param list_tup_piezometre: liste des piezometre
        :type list_tup_piezometre: list

        :param couche_courante: couche vecteur selectionnee
        :type couche_courante: QgsVectorLayer

        :param num_iteration_progressbar: etape du tölöchargement
        :type num_iteration_progressbar: int

        :param nb_req: Nombre d'etape total du téléchargement
        :type nb_req: int

        :return: url dossier
        :rtype: str
        """

        try:
            self.dockwidget.pb_annuler.setEnabled(True)
            self.dockwidget.progressBar.setRange(num_iteration_progressbar, nb_req)
            df_data_piezo = pd.DataFrame()
            for code_bss, coord_x, coord_y in list_tup_piezometre:
                self.controler_interruption_utilisateur()
                # Boucle sur les paramètres demandés (uniquement piézo pour l'instant !)
                # Un seul paramètre quantite possible actuellement
                list_code_parametre_quantite = self.pconfig.list_lex_parametre_quantite
                for code_parametre in list_code_parametre_quantite:
                    self.controler_interruption_utilisateur()
                    if (self.stop is False):  # control interuption
                        # On lance la requête Hubeau
                        df_req, statut_req = self.preq.requete_hubeau_par_point(code_bss, [], [code_parametre], "chroniques_piezo_csv")
                        # Si le résultat de la requête est correct on ajoute les données au df résultat
                        if statut_req == 200:
                            df_req["x_wgs84"] = coord_x
                            df_req["y_wgs84"] = coord_y
                            if len(df_data_piezo) > 0:
                                df_data_piezo = df_data_piezo.append(df_req)
                            else:
                                df_data_piezo = df_req
                        # Si le résultat est incorrect on lève une exception gérée et on avertit l'utilisateur
                        else:
                            raise ErreurResultatRequeteIncorrect
                        # Mise à jour du progressbar
                        num_iteration_progressbar += 1
                        self.dockwidget.progressBar.setValue(num_iteration_progressbar)

            # Si le df résultat pour les chroniques piézométriques contient des données
            self.dockwidget.pb_annuler.setEnabled(False)  # dernière étape oú il est possible d'annuler
            self.controler_interruption_utilisateur()
            if (self.stop is False):
                if len(df_data_piezo) > 0:

                    chemin_fichier_geopackage = UtilitaireCouches.get_chemin_fichier_geopackage(couche_courante)
                    # chemin_dossier_geopackage = self.get_chemin_dossier_geopackage(chemin_fichier_geopackage)
                    chemin_dossier_geopackage = UtilitaireCouches.get_chemin_dossier_geopackage(chemin_fichier_geopackage)

                    # Suppression des doublons du df résultat (doublons ADES) et tri
                    df_data_piezo = df_data_piezo.drop_duplicates()
                    df_data_piezo = df_data_piezo.sort_values(['code_bss', 'date_mesure'])     # En attendant de disposer de id_bss !

                    # Création du sous-dossier qui contiendra les résultats d'analyse et le geopackage des points correspondantes
                    nb_point = str(df_data_piezo['code_bss'].unique().shape[0])
                    horodate_resultat = datetime.datetime.now().strftime('%y%m%d%H%M%S')
                    nom_dossier_resultat = f"Résultats_Piézométrie_{nb_point}_points_{horodate_resultat}"
                    chemin_dossier_resultat = os.path.join(chemin_dossier_geopackage, nom_dossier_resultat)
                    os.mkdir(chemin_dossier_resultat)
                    chemin_geopackage_resultat = os.path.join(chemin_dossier_resultat, nom_dossier_resultat + '.gpkg')

                    # Création du groupe qui contiendra les couches de points par paramètre
                    groupe_parent_couche_courante = self.iface.layerTreeView().currentGroupNode()
                    groupe_couche = groupe_parent_couche_courante.addGroup(nom_dossier_resultat)

                    # Création du df des métadonnées des points d'eau et écriture d'un csv temporaire
                    df_infos = df_data_piezo[self.preq.list_col_metadata_niveaux_nappes_chroniques_csv + ['x_wgs84', 'y_wgs84']]
                    df_infos['code_param'] = ''
                    df_infos['nom_param'] = 'Niveaux_Piézométriques'
                    df_infos = df_infos.drop_duplicates()
                    chemin_csv_temp = os.path.join(chemin_dossier_resultat, "Temp.csv")
                    self.pio.ecrire_fichier_csv(df_infos, chemin_csv_temp)

                    # Lecture du fichier csv temporaire qui vient d'être écrit sur le disque et création d'une couche qgis temporaire sans ajout à la carte
                    couche_infos = self.lire_couche_csv(chemin_csv_temp, "Couche_Temporaire", ";",
                                                        champ_x="x_wgs84", champ_y="y_wgs84", epsg="EPSG:4326", ajouter_carte=False)

                    # Ecriture de la couche qgis en mémoire dans un nouveau geopackage avec reprojection dans la projection demandée par l'utilisateur
                    epsg_reproj = self.get_epsg_selectionnee()
                    self.ecrire_couche_geopackage(chemin_geopackage_resultat, couche_infos, "Points_Niveaux_Piézométriques", "EPSG:4326", epsg_reproj, ajouter_couche=False)

                    # Lecture du geopackage et ajout de la nouvelle couche dans le nouveau groupe de couches des résultats
                    self.lire_couche_geopackage(chemin_geopackage_resultat, "Points_Niveaux_Piézométriques", groupe_couche, developper_groupe=False)

                    # Création du df des niveaux piézométriques et écriture au format csv
                    df_resultat = df_data_piezo[['code_bss'] + self.preq.list_col_data_niveaux_nappes_chroniques_csv]
                    df_resultat['commentaire'] = 'Correct'  # Ajout d'un champ commentaire pour que l'utilisateur puisse commenter chaque analyse
                    nom_csv_resultat = f"Données_Niveaux_{horodate_resultat}.csv"
                    chemin_csv_resultat = os.path.join(chemin_dossier_resultat, nom_csv_resultat)
                    self.pio.ecrire_fichier_csv(df_resultat, chemin_csv_resultat)

                    # Lecture du fichier csv des niveaux piézométriques qui vient d'être écrit sur le disque et création d'une couche qgis temporaire sans ajout à la carte
                    couche_donnees_niveaux = self.lire_couche_csv(chemin_csv_resultat, "Couche_Temporaire_Data_Niveaux", ";", ajouter_carte=False)

                    # Ajout de la couche des analyses chimiques dans le geopackage déjà existant
                    self.ecrire_couche_geopackage(chemin_geopackage_resultat, couche_donnees_niveaux, nom_csv_resultat, ajouter_couche=True)

                    # Lecture du geopackage et ajout de la nouvelle couche des analyses chimiques dans le nouveau groupe de couches des résultats
                    self.lire_couche_geopackage(chemin_geopackage_resultat, nom_csv_resultat, groupe_couche, developper_groupe=False)

                    self.dockwidget.progressBar.setValue(nb_req)  # progress bar 100%

                    self.iface.messageBar().pushMessage("Le téléchargement des données est terminé.", "Données disponibles")

                else:
                    self.iface.messageBar().pushWarning(
                        """La requête vers Hubeau n'a renvoyé aucun résultat :
                        il n'existe aucune chronique piézométrique correspondant à la sélection de points effectuée."""
                    )

            self.dockwidget.progressBar.reset()

        except ErreurInterruptionUtilisateur:
            self.iface.messageBar().pushMessage("Opération interrompue par l'utilisateur : " +
                                                "le téléchargement des données est incomplet...",
                                                Qgis.Critical)

    def get_epsg_selectionnee(self) -> str:
        """
        Obtenir le CRS sélectionné par l'utilisateur

        :return: Crs sous la forme "EPSG:2154"
        :rtype: str
        """
        # Renvoie le crs sélectionné par l'utilisateur (objet)
        crs_reproj = self.dockwidget.qgs_projection.crs()
        # Renvoie le crs (p.ex sous la forme "EPSG:2154")
        epsg_reproj = crs_reproj.authid()
        return epsg_reproj









    # def obtenir_liste_attribut_point_selectionne(self, nom_attribut):
    #     """
    #     Fonction qui parcourt l'ensemble des couches chargées dans Qgis
    #     et extrait pour chaque point sélectionné la valeur de l'attribut
    #     dont le nom est passé en paramètre.
    #     :return:
    #     """
    #     list_attribut = []
    #     nb_erreur_couche = 0
    #     nb_erreur_point = 0
    #     layers = QgsProject.instance().mapLayers().values()
    #     for layer in layers:
    #         try:
    #             for selected_points in layer.getSelectedFeatures():
    #                 try:
    #                     list_attribut.append((layer.name(), selected_points[nom_attribut]))
    #                 except:
    #                     nb_erreur_point += 1
    #         except:
    #             nb_erreur_couche += 1
    #     return (list_attribut, nb_erreur_couche, nb_erreur_point)

    # # Connecte le bouton de choix d'un fichier out (toolButton) à la fonction de désactivation de tous les widgets
    # self.dockwidget.le_choisirFichier.textChanged.connect(self.pX_desactiverWidgets)

    #     num_page = self.dockwidget.tabWidget.currentIndex()
    #     if num_page == 0:
    #         chemin_fichier_out = str(QFileDialog.getOpenFileName(
    #                                  caption="Sélectionnez un fichier de grille MARTHE (version 9.0)",
    #                                  filter="Fichiers MARTHE (*.*)")[0])
    #         if (chemin_fichier_out is not None) and (chemin_fichier_out != ""):
    #             try:
    #                 with open(chemin_fichier_out, 'r') as f:
    #                     # lève une erreur si le format de fichier n'est pas 9.0
    #                     first_row = f.readline()
    #                     if first_row.startswith('Marthe_Grid Version=9.0') == False:
    #                         pass
    #                     else:
    #                         # Affiche le nom du fichier choisi par l'utilisateur dans la ligne de texte
    #                         self.dockwidget.le_choisirFichier.setText(chemin_fichier_out)
    #                         # Initialise et désactive les widgets de la page
    #                         # self.pX_initialiserWidgets(num_page)
    #                         self.pX_desactiverWidgets(num_page)
    #             except:
    #                 self.iface.messageBar().pushMessage("Ce n'est pas un fichier de grilles MARTHE ou la version "
    #                                                     + "du fichier est différente de la 9.0 : opération abandonnée...",
    #                                                     Qgis.Critical)
    #

    #                 # Recherche du groupe de couche éventuel dans lequel écraser et/ou ajouter les couches
    #                 self.groupe_couches = self.root.findGroup(os.path.basename(chemin_dossier_resultat))
    #                 # Si le groupe de couches existe, définition d'un indicateur d'existence et remplissage d'un dictionnaire
    #                 if self.groupe_couches is not None:
    #                     groupe_existant = True
    #                     # Construit un dictionnaire nom / id des couches du groupe existant
    #                     for child in self.groupe_couches.children():
    #                         if isinstance(child, QgsLayerTreeLayer):
    #                             self.dict_couches_groupe_existant[child.name()] = child.layerId()
    #                 # Si le groupe de couches n'existe pas, indicateur d'existence du groupe de couche mis à False
    #                 else:
    #                     groupe_existant = False
    #             # Si le dossier résultat choisi est vide
    #             if os.listdir(chemin_dossier_resultat) == []:
    #                 dossier_resultat_vide = True
    #             # Si le dossier résultat choisi n'est pas vide : test pour savoir si l'utilisateur veut continuer
    #             else:
    #                 dossier_resultat_vide = False

    #         # Supprime tous les fichiers de métadonnées créés par gdal lors de la suppression des couches
    #         # (ne marche que le coup d'après car le processus python en cours interdit la suppression)
    #         # Expression de recherche des fichiers .aux.xml créés par gdal dans le dossier résultat à chaque suppression de couche
    #         recherche_fichier = os.path.join(chemin_dossier_resultat, "*.aux.xml")

    #         # Suppression des fichiers pdf qui respectent l'expression de recherche
    #         for fichier_aux_xml in glob.glob(recherche_fichier):
    #             # os.remove(fichier_aux_xml)
    #             self.supprimerFichierParShellWindows(fichier_aux_xml)