# -*- coding: utf-8 -*-
"""
@author: Laurent Vaute
email: l.vaute@brgm.fr
copyright: (C) 2019 by BRGM

Module de PickEau  : tracé de graphiques interactifs correspondants à des points sélectionnés
d'une couche active, affectation de commentaires à des lignes de données sélectionnées.
"""
import os
from PyQt5.QtWidgets import QDockWidget, QAction
from qgis.PyQt.QtCore import QUrl, QDate
from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtGui import QIcon
from qgis.core import *
from qgis.utils import plugins


from functools import partial
import re
import json
import importlib

# Add by Bgrenard --> improve it later
plotly_installee = True
try:
    from DataPlotly.data_plotly_plot import *   # Importe la classe Plot du module data_plotly_plot
    from DataPlotly.utils import *  # Importe les fonctions utilitaires du module utils (dont getIds et getSortedId)
except:
    plotly_installee = False


# Définition des exceptions gérées par les fonctions des classes du module
class Error(Exception):
   """Base class for other exceptions."""
   pass
class ErreurCreationCoucheDonnees(Error):
   """Exception gérée levée lorsque la couche Qgis n'a pas pu être créée à partir du fichier source."""
   pass
class ErreurTypeCouchePointSelectionnee(Error):
   """Exception gérée levée lorsque la couche Qgis active n'appartient pas
   à un groupe de couches de type Qualité ou Quantité créé par PickEau."""
   pass


class Pick_Pg_Graph():
    """
    Classe liée au dockwidget gauche de l'interface de PickEau :
        - tracé des chroniques sélectionnées sur un graphique interactif
        - affectation de commentaires aux lignes de données sélectionnées
    Cette classe prend en paramètres plusieurs instances des modules de PickEau :
        - pickeau_graph_dockwidget.PickEauGraphDockWidget : widget qt contenant les objets de l'interface de PickEau
        - pick_configuration.Pick_Config : fonctions de configuration du plugin PickEau
        - pick_requete.Pick_Req : fonctions d'envoi de requêtes sur les serveurs Hubeau, Sandre, Ades
        - pick_utilitaire.Pick_IO : fonctions de lecture / écriture de fichiers externes
        - pick_utilitaire.Pick_Tools : fonctions utilitaires diverses
    """

    def __init__(self, iface, graphDockwidget, pio, ptools, pconfig, preq):

        # Définition des attributs de la classe = objets de la classe PickEau passés en paramètre
        self.iface = None   # pour éviter les problèmes au rechargement du plugin (https://gis.stackexchange.com/questions/289330/passing-self-when-calling-functions-in-modules-from-other-modules-using-pyqgis)
        self.iface = iface
        self.pconfig = pconfig
        self.preq = preq
        self.pio = pio
        self.ptools = ptools
        self.graphDockwidget = graphDockwidget

        if plotly_installee is True:

            # Définition du dockwidget DataPlotly pour pouvoir agir dessus depuis PickEau
            self.dataPlotlyDockwidget = self.iface.mainWindow().findChild(QDockWidget, 'DataPlotlyDockWidgetBase')

            # Définition d'un dictionnaire clé = nom PickEau du graphique / valeur = objet graphique DataPlotly
            self.dict_graph_dataplotly = {}
            # Définition d'un dictionnaire vide clé = uid des traces (graphiques) / propriétés du script html
            # nécessaires à l'interaction graphique - table de données - carte
            # self.dict_uid_graph = {}

            # Attributs dont le contenu sera défini / modifié plus tard par les fonctions de la classe
            self.attribute_dockwidget = None
            self.data_layer = None
            self.dp = None
            self.type_data = None
            self.code_parametre = None
            self.nom_parametre = None
            self.type_graphique = None
            self.point_layer = None
            self.ecraser_graphique = True
            self.plot_path = None

            # Widgets de filtre sur les données
            date_debut = QDate.fromString('01/01/1900', 'dd/MM/yyyy')
            date_fin = QDate.fromString('01/01/2100', 'dd/MM/yyyy')
            self.graphDockwidget.de_dateDebutChronique.setDate(date_debut)
            self.graphDockwidget.de_dateFinChronique.setDate(date_fin)
            self.graphDockwidget.cbx_choisirQualificationAdes.addItems(self.pconfig.list_lex_qualification_ades)
            self.graphDockwidget.cbx_choisirCommentairePickEau.addItems(self.pconfig.list_lex_commentaire_pickeau)

            # Widgets de mise en page des graphiques
            self.graphDockwidget.rdb_ajouterGraphe.toggled.connect(self.ajouter_graphe)
            self.graphDockwidget.rdb_ajouterGraphe.setChecked(True)
            self.graphDockwidget.rdb_ecraserGraphe.toggled.connect(self.ecraser_graphe)
            self.graphDockwidget.cbx_choisirDispositionGraphe.addItems(self.pconfig.list_lex_disposition_graphe)
            self.graphDockwidget.cbx_choisirDispositionGraphe.setCurrentIndex(1)   # positionne sur "Juxtaposer en colonne"

            # Widgets de tracé des graphiques
            self.graphDockwidget.pbt_tracerGraphiqueCourbe.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons/pickeau_icon.png')))
            self.graphDockwidget.pbt_tracerGraphiqueBoxplot.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons/boxplot.svg')))
            self.graphDockwidget.pbt_tracerGraphiqueHistogramme.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons/histogram.svg')))
            self.graphDockwidget.pbt_tracerGraphiqueCourbe.clicked.connect(self.bouton_tracer_courbe_active)
            self.graphDockwidget.pbt_tracerGraphiqueBoxplot.clicked.connect(self.bouton_tracer_boxplot_active)
            self.graphDockwidget.pbt_tracerGraphiqueHistogramme.hide()
            self.graphDockwidget.pbt_tracerGraphiqueHistogramme.clicked.connect(self.bouton_tracer_histogramme_active)
            # self.graphDockwidget.ckx_activerGrapheAuto.stateChanged.connect(self.activer_graphe_auto)  # supprimé dans la version actuelle
            self.graphDockwidget.cbx_choisirGraphiqueDataPlotly.addItems(["Tous"])
            self.graphDockwidget.pbt_effacerGraphique.clicked.connect(self.effacer_graphique)
            self.graphDockwidget.pbt_formaterGraphique.hide()  # TODO activer la fonctionnalité de formatage

            # Widgets d'affichage et de commentaire des données
            self.graphDockwidget.pbt_afficherDataTable.clicked.connect(self.afficher_data_table)
            # self.graphDockwidget.cbx_choisirTableData
            self.graphDockwidget.cbx_choisirTypeCommentaire.addItems(self.pconfig.list_lex_type_commentaire)
            self.graphDockwidget.pbt_commenterSelectedDataRows.clicked.connect(self.commenter_selected_data_rows)
            self.graphDockwidget.pbt_annulerCommentaires.clicked.connect(self.annuler_commentaires)
            self.graphDockwidget.pbt_enregistrerCommentaires.clicked.connect(self.enregistrer_commentaires)

            # Connecte le widget statusBarMessage de DataPlotly à la fonction de sélection des points sur la carte
            # (DataPlotly envoie par ce biais les informations sur la couche et le point sélectionné)
            self.dataPlotlyDockwidget.plot_view.statusBarMessage.connect(self.selectionner_data_et_points)

    # ==========================================================================
    # Fonctions de mise en page
    # ==========================================================================

    def ecraser_graphe(self, on):
        """
        Fonction qui positionne la paire de boutons radio sur 'Ecraser'
        """
        if on:
            self.ecraser_graphique = True
            self.graphDockwidget.cbx_choisirDispositionGraphe.setEnabled(False)


    def ajouter_graphe(self, on):
        """
        Fonction qui positionne la paire de boutons radio sur 'Ajouter'
        """
        if on:
            self.ecraser_graphique = False
            self.graphDockwidget.cbx_choisirDispositionGraphe.setEnabled(True)

    # ==========================================================================
    # Fonctions de tracé de graphiques
    # ==========================================================================

    def bouton_tracer_courbe_active(self):
        self.type_graphique = 'scatter'
        self.tracer_graphique_main()


    def bouton_tracer_boxplot_active(self):
        self.type_graphique = 'box'
        self.tracer_graphique_main()


    def bouton_tracer_histogramme_active(self):
        # self.type_graphique = 'histogramme'
        # self.tracer_graphique_main()
        pass


    def tracer_graphique_main(self):
        """
        Fonction qui s'exécute sur appui de l'un des boutons 'pbt_tracerGraphique*'
        et qui lance la fonction de tracé des graphiques correspondants :
        - au type de graphique demandé
        - aux points sélectionnés sur la carte
        - à la couche active (sélectionnée dans la liste des couches) si c'est un paramètre téléchargé par PickEau.
        """
        # Couche dont les points sont sélectionnés
        self.point_layer = self.iface.activeLayer()
        
        # Si une couche de points téléchargée par PickEau est sélectionnée
        if self.point_layer and "Points_" in self.point_layer.name():
            
            # Extraction du code sandre et du nom du paramètre correspondant à la couche
            nom_couche = self.point_layer.name()
            self.code_parametre = nom_couche[nom_couche.rfind("_") + 1::]
            self.nom_parametre = nom_couche[nom_couche.find("_") + 1:nom_couche.rfind("_")]
    
            # Appel de la fonction de recherche de la table de données
            # du groupe de couches résultat qui est actif.
            self.rechercher_data_layer()
    
            # Construction de la liste des points bss sélectionnés
            list_code_bss = []
            for feature in self.point_layer.getSelectedFeatures():
                # Construction de la liste des codes_bss des points sélectionnés
                list_code_bss.append(feature['code_bss'])

            # S'il y a au moins un point sélectionné
            if len(list_code_bss) > 0:
                # Si le type de graphique est de type 'scatter' (détourné pour tracer des courbes temporelles)
                if self.type_graphique == 'scatter':
                    # Boucle sur tous les points sélectionnés
                    for code_bss in list_code_bss:
                        # Filtre la table de données selon le code bss du point
                        self.construire_filtre_donnee([code_bss])
                        # Appel de la fonction de tracé de graphique sur DataPlotly
                        self.tracer_graphique_dataplotly(id_point=code_bss)

                # Si le type de graphique est de type boxplot
                elif self.type_graphique == 'box':
                    # Filtre la table de données selon le code bss du point
                    self.construire_filtre_donnee(list_code_bss)
                    # Appel de la fonction de tracé de graphique sur DataPlotly
                    self.tracer_graphique_dataplotly()
            # Si pas de point sélectionné dans la couche active
            else:
                self.iface.messageBar().pushMessage("Au moins un point de la couche active doit être sélectionné !",
                                                    Qgis.Critical)
            
        # Si pas de couche active
        else:
            self.iface.messageBar().pushMessage("Activez une couche de points téléchargée par PickEau (cliquez sur son nom dans la liste des couches) pour pouvoir tracer un graphique ! ",
                                                Qgis.Critical)


    def rechercher_data_layer(self):
        """
        Fonction de recherche de la couche de données associée
        à la couche qui contient les points sélectionnés.
        """
        # L'ensemble de la fonction est incluse dans un bloc try de niveau le plus haut pour capturer
        # tous les types d'erreurs gérés (par "raise") : chaque erreur gérée rencontrée est remontée
        # jusqu'à ce niveau et passée au bloc "except" correspondant (voir en bas de la fonction).
        # Il est possible d'insérer des structures try - except de niveau inférieur, chaque except de niveau
        # inférieur devant lever par "raise" une exception gérée qui remontera jusqu'au niveau supérieur.
        try:
            # Indicateur de chargement de la couche de données dans le groupe de couches de la couche active
            data_layer_charge = False
            # Groupe parent de la couche active (en bleu dans la liste des couches)
            self.groupe_parent_point_layer = self.iface.layerTreeView().currentGroupNode()
            nom_grp_parent = self.groupe_parent_point_layer.name()
            horodatage = nom_grp_parent[nom_grp_parent.rfind("_") + 1::]
            # On parcourt la liste des noeuds du groupe parent
            for child_node in self.groupe_parent_point_layer.children():
                # S'il s'agit d'un objet de type noeud de couche
                if isinstance(child_node, QgsLayerTreeLayer):
                    # Instanciation de la couche correspondant au noeud de couche et récupération de son nom
                    layer = child_node.layer()
                    layer_name = layer.name()
                    # Si la couche est une couche de données d'analyses chimiques
                    if "Données_Analyses_" in layer_name:
                        self.data_layer = layer
                        self.type_data = "analyse"
                        data_layer_charge = True
                    # Si la couche est une couche de données de niveaux piézométriques
                    if "Données_Niveaux_" in layer_name:
                        self.data_layer = layer
                        self.type_data = "niveau"
                        data_layer_charge = True

            # Si la couche de données n'est pas trouvée dans le groupe parent on la charge depuis le geopackage
            if data_layer_charge == False:
                try:
                    # Chemin du geopackage contenant la couche des points sélectionnés
                    chemin_geopackage = self.point_layer.dataProvider().dataSourceUri().split('|')[0]
                except:
                    raise ErreurTypeCouchePointSelectionnee
                # Recherche du type de données contenues dans le groupe parent
                if "Qualité" in self.groupe_parent_point_layer.name():
                    nom_couche = "Données_Analyses_" + horodatage
                    self.type_data = "analyse"
                elif "Niveaux" in self.groupe_parent_point_layer.name():
                    nom_couche = "Données_Niveaux_" + horodatage
                    self.type_data = "niveau"
                else:
                    raise ErreurTypeCouchePointSelectionnee
                # Chargement de la couche de données du géopackage
                gpkg_layer = QgsVectorLayer(chemin_geopackage + "|layername=" + nom_couche, nom_couche, 'ogr')
                # En cas d'erreur de chargement
                if not gpkg_layer.isValid():
                    raise ErreurCreationCoucheDonnees
                # Si la couche est correcte, ajout de la couche au groupe parent
                QgsProject.instance().addMapLayer(gpkg_layer, False)
                new_layer_node = self.groupe_parent_point_layer.addLayer(gpkg_layer)
                # Instanciation de la couche de données associée à la couche de points
                self.data_layer = new_layer_node.layer()
                data_layer_charge = True

            # Connecte l'événement de changement des lignes sélectionnées de la table de données
            # à la fonction de sélection des points correspondants sur la carte
            # NB : utilise la fonction 'partial' pour transmettre l'objet data_layer en même temps que
            # les 3 paramètres du signal 'selectionChanged' (list_ids_selected_rows, list_ids_deselected_rows, option_clear_and_select)
            # self.data_layer.selectionChanged.connect(partial(self.selectionner_points_carte, self.data_layer))


        # Gestion des erreurs
        except ErreurCreationCoucheDonnees:
            self.iface.messageBar().pushMessage("La couche de données associée aux points d'eau sélectionnés n'existe pas dans le geopackage !",
                                                Qgis.Critical)
        except ErreurTypeCouchePointSelectionnee:
            self.iface.messageBar().pushMessage("La couche de points sélectionnée n'est pas une couche de résultats créée par PickEau !",
                                                Qgis.Critical)


    def selectionner_data_et_points(self, status):
        """
        Fonction qui sélectionne les lignes de données et les points sur la carte
        correspondants aux données cliquées ou sélectionnées sur le graphique DataPlotly.
        La fonction s'active à la réception d'un signal statusBarMessage émis par PLOT.js_callback.
        Cette fonction s'exécute juste après la fonction getJSmessage de DataPlotly qui réagit au même signal
        et a un but similaire mais n'agit que sur la table de données.

        the method handles several exceptions:
            the first try/except is due to the connection to the init method

            second try/except looks into the decoded status, that is, it decodes
            the js dictionary and loop where it is necessary

            the dic js dictionary contains several information useful to handle
            correctly every operation
        """
        try:
            # Décode le contenu du signal
            dic_status = json.JSONDecoder().decode(status)

            # Itère sur le dict des graphiques pour obtenir les infos caractéristiques du graphique
            # associées à l'uid défini par Plotly pour la trace et qui est contenu dans le status
            for tup_graph in self.dict_graph_dataplotly.items():
                nom_graph = tup_graph[0]
                dict_graph = tup_graph[1]
                if dict_graph["uid_plotly"] == dic_status['uid']:
                    # Instancie le groupe de couches associé au graphique
                    nom_groupe_couches = dict_graph["nom_groupe_couches"]
                    root = QgsProject.instance().layerTreeRoot()
                    groupe_couches = root.findGroup(nom_groupe_couches)
                    # Instancie les couches de points associées au graphique
                    id_couche_point = dict_graph["id_couche_point"]
                    id_couche_data = dict_graph["id_couche_data"]
                    couche_point = groupe_couches.findLayer(id_couche_point).layer()
                    couche_data = groupe_couches.findLayer(id_couche_data).layer()
                    # Supprime la sélection déjà existantes de points et de données
                    # (notamment celle qui vient d'être effectuée par DataPlotly)
                    # couche_data.removeSelection()
                    # Définit le type de données
                    type_data = dict_graph["type_data"]
                    # Définit le nom du paramètre
                    nom_parametre = dict_graph["nom_parametre"]

        except:
            dic_status = None

        try:
            # if a selection event is performed
            if dic_status['mode'] == 'selection':

                if dic_status['type'] == 'scatter':
                    couche_data.selectByIds(dic_status['id'])

            # if a clicking event is performed depending on the plot type
            elif dic_status["mode"] == 'clicking':

                if dic_status['type'] == 'scatter':
                    couche_data.selectByIds([dic_status['fidd']])
                elif dic_status['type'] == 'box':
                    if type_data == 'analyse':
                        expr = f'"{dic_status["field"]}" = \'{dic_status["id"]}\' AND "nom_param" = \'{nom_parametre}\''
                    else:
                        # build the expression from the js dic_status (customdata)
                        expr = f'"{dic_status["field"]}" = \'{dic_status["id"]}\''
                    # set the iterator with the expression as filter in feature request
                    request = QgsFeatureRequest().setFilterExpression(expr)
                    it = couche_data.getFeatures(request)
                    couche_data.selectByIds([f.id() for f in it])

            list_code_param = []
            list_code_bss = []

            # Obtient la liste des lignes sélectionnées de la table de données
            iter_selected_rows = couche_data.getSelectedFeatures()
            # Boucle sur chaque ligne pour sélectionner la liste des codes paramètre et des codes bss
            # en supprimant les doublons
            for row in iter_selected_rows:
                if 'Données_Analyses_' in couche_data.name():
                    list_code_param.append(row['code_param'])
                    list_code_bss.append(row['code_bss'])
                elif 'Données_Niveaux_' in couche_data.name():
                    list_code_param.append("Niveaux")
                    list_code_bss.append(row['code_bss'])
            # Suppression des doublons des listes de points et de paramètres
            list_code_param = list(set(list_code_param))
            list_code_bss = list(set(list_code_bss))

            # Pour chaque code paramètre de la liste
            for code_param in list_code_param:
                # On parcourt la liste des noeuds du groupe parent
                for child_node in groupe_couches.children():
                    # S'il s'agit d'un objet de type noeud de couche
                    if isinstance(child_node, QgsLayerTreeLayer):
                        # Instanciation de la couche correspondant au noeud de couche et récupération de son nom
                        layer = child_node.layer()
                        layer_name = layer.name()
                        # Si le code paramètre est trouvé dans le nom de la couche et que ce n'est pas une couche de données
                        if (str(code_param) in layer_name) and ("Données_" not in layer_name):
                            # Instanciation de la couche de points
                            point_layer = layer
                            # Active la couche dans l'arbre des couches
                            self.iface.layerTreeView().setCurrentLayer(point_layer)
                            break
                # Sélectionne par une expression les points bss de la couche de points
                expr = f'("code_bss" IN ({str(list_code_bss)[1:-1]}))'
                couche_point.selectByExpression(expr, QgsVectorLayer.SetSelection)

        except:
            pass


    # def selectionner_points_carte(self, data_layer, list_ids_selected_rows, list_ids_deselected_rows, option_clear_and_select):
    #     """
    #     Fonction activée par le signal 'selectionChanged' émis par une table de données
    #     --> sélectionne à son tour les points correspondants sur la carte. La connection
    #     entre la table de données qui emet le signal et cette fonction se fait lors de l'exécution
    #     de la fonction 'rechercher_data_layer' elle-même appelée lors du tracé d'un graphique
    #     ('tracer_graphique_main') ou de l'affichage d'une table de données ('afficher_data_table')
    #     """
    #     list_code_param = []
    #     list_code_bss = []
    #
    #     # Recherche le groupe parent de la table de données qui a émis le signal selectionChanged
    #     root = QgsProject.instance().layerTreeRoot()
    #     root_layer = root.findLayer(data_layer.id())
    #     if root_layer:
    #         groupe_parent_data_layer = root_layer.parent()
    #     else:
    #         pass
    #
    #     # Obtient la liste des lignes sélectionnées de la table de données qui a émis le signal selectionChanged
    #     iter_selected_rows = data_layer.getSelectedFeatures()
    #     # Boucle sur chaque ligne pour sélectionner la liste des codes paramètre et des codes bss
    #     # en supprimant les doublons
    #     for row in iter_selected_rows:
    #         if 'Données_Analyses_' in data_layer.name():
    #             list_code_param.append(row['code_param'])
    #             list_code_bss.append(row['code_bss'])
    #         elif 'Données_Niveaux_' in data_layer.name():
    #             list_code_param.append("Niveaux")
    #             list_code_bss.append(row['code_bss'])
    #     # Suppression des doublons des listes de points et de paramètres
    #     list_code_param = list(set(list_code_param))
    #     list_code_bss = list(set(list_code_bss))
    #
    #     # Pour chaque code paramètre de la liste
    #     for code_param in list_code_param:
    #         # On parcourt la liste des noeuds du groupe parent
    #         for child_node in groupe_parent_data_layer.children():
    #             # S'il s'agit d'un objet de type noeud de couche
    #             if isinstance(child_node, QgsLayerTreeLayer):
    #                 # Instanciation de la couche correspondant au noeud de couche et récupération de son nom
    #                 layer = child_node.layer()
    #                 layer_name = layer.name()
    #                 # Si le code paramètre est trouvé dans le nom de la couche et que ce n'est pas une couche de données
    #                 if (str(code_param) in layer_name) and ("Données_" not in layer_name):
    #                     # Instanciation de la couche de points
    #                     point_layer = layer
    #                     # Active la couche dans l'arbre des couches
    #                     self.iface.layerTreeView().setCurrentLayer(point_layer)
    #                     break
    #         # Sélectionne par une expression les points bss de la couche de points
    #         expr = f'("code_bss" IN ({str(list_code_bss)[1:-1]}))'
    #         point_layer.selectByExpression(expr, QgsVectorLayer.SetSelection)


    def construire_filtre_donnee(self, list_code_bss):
        """
        Filtre les lignes de la couche de données selon les points
        sélectionnés de la couche de points. Si le paramètre list_code_bss
        est une liste vide [] tout filtre existant est supprimé.
        """
        date_debut = self.graphDockwidget.de_dateDebutChronique.date().toString('yyyy-MM-dd')
        date_fin = self.graphDockwidget.de_dateFinChronique.date().toString('yyyy-MM-dd')
        qualification = self.graphDockwidget.cbx_choisirQualificationAdes.currentText()
        commentaire = self.graphDockwidget.cbx_choisirCommentairePickEau.currentText()

        if len(list_code_bss) > 0:

            # Si les données sont des analyses chimiques
            if self.type_data == "analyse":

                # Construction du fragment principal de l'expression de filtre
                expr_principal = f'("code_bss" IN ({str(list_code_bss)[1:-1]})) \
                                 AND ("code_param" = {self.code_parametre}) \
                                 AND ("date_debut_prelevement" >= \'{date_debut}\') \
                                 AND ("date_debut_prelevement" <= \'{date_fin}\')'

                # Construction du fragment de filtre concernant la qualification ADES des données
                if qualification == 'Correcte uniquement':
                    expr_qualification = ' AND ("nom_qualification" LIKE \'Correcte\')'
                elif qualification == 'Toutes':
                    expr_qualification = ''
                elif qualification == 'Exclure incorrecte':
                    expr_qualification = ' AND ("nom_qualification" NOT LIKE \'Incorrecte\')'
                elif qualification == 'Exclure incertaine':
                    expr_qualification = ' AND ("nom_qualification" NOT LIKE \'Incertaine\')'
                elif qualification == 'Exclure non définissable':
                    expr_qualification = ' AND ("nom_qualification" NOT LIKE \'Qualification non définissable\')'

                # Construction du fragment de filtre concernant la validité du résultat
                expr_resultat = ' AND ("resultat" IS NOT NULL)'

            # Si les données sont des niveaux piézométriques
            if self.type_data == "niveau":

                # Construction du fragment principal de l'expression de filtre
                expr_principal = f'("code_bss" IN ({str(list_code_bss)[1:-1]})) \
                     AND ("date_mesure" >= \'{date_debut}\') \
                     AND ("date_mesure" <= \'{date_fin}\')'

                # Construction du fragment de filtre concernant la qualification ADES des données
                if qualification == 'Toutes':
                    expr_qualification = ''
                elif qualification == 'Correcte uniquement':
                    expr_qualification = ' AND ("qualification" LIKE \'Correcte\')'
                elif qualification == 'Exclure incorrecte':
                    expr_qualification = ' AND ("qualification" NOT LIKE \'Incorrecte\')'
                elif qualification == 'Exclure incertaine':
                    expr_qualification = ' AND ("qualification" NOT LIKE \'Incertaine\')'
                elif qualification == 'Exclure non définissable':
                    expr_qualification = ' AND ("qualification" NOT LIKE \'Qualification non définissable\')'

                # Construction du fragment de filtre concernant la validité du résultat
                expr_resultat = ' AND ("niveau_nappe_eau" IS NOT NULL)'

            # Construction du fragment de filtre concernant le commentaire PickEau des données
            if commentaire == 'Correct uniquement':
                expr_commentaire = ' AND ("commentaire" LIKE \'Correct\')'
            elif commentaire == 'Tous':
                expr_commentaire = ''
            elif commentaire == 'Exclure aberrant':
                expr_commentaire = ' AND ("commentaire" NOT LIKE \'Aberrant\')'
            elif commentaire == 'Exclure douteux':
                expr_commentaire = ' AND ("commentaire" NOT LIKE \'Douteux\')'
            # expr_commentaire = ''

            # Concaténation des fragments d'expression de filtre
            expr = expr_principal + expr_qualification + expr_commentaire + expr_resultat

        else:
            expr = ''

        # Construit la requête qui sera utilisée pour obtenir les lignes correspondant au filtre
        self.request = QgsFeatureRequest().setFilterExpression(expr)

        # Filtrage de la couche
        # self.data_layer.setSubsetString(expr)

        # Rafraichit la liste des couches
        # self.iface.layerTreeView().refreshLayerSymbology(self.data_layer.id())


    # ==========================================================================
    # Fonctions de tracé des graphiques issues de DataPlotly
    # ==========================================================================


    def tracer_graphique_dataplotly(self, id_point=''):
        """
        Trace un graphique dans le plugin DataPlotly en lui passant un dictionnaire
        qui contient son type et la référence des données à tracer ainsi que
        toutes les propriétés du graphique (plot_prop) et de sa mise en page (layout_prop)
        """
        # Appel de la fonction de vérification du chargement des plugins
        self.verifier_chargement_plugins()
        # Affichage du dockwidget DataPlotly
        self.dataPlotlyDockwidget.show()
        # Mise au premier plan de l'onglet du dockwidget DataPlotly
        self.dataPlotlyDockwidget.raise_()

        # ===================================

        # Equivalent de la fonction plotProperties de la classe DataPlotlyDockWidget
        # avec passage d'un dictionnaire personnalisé de propriétés du graphique

        # Nom des champs de données en fonction du type de donnée
        if self.type_data == 'niveau':
            point_code = 'code_bss'
            x_time = 'date_mesure'
            y_data = 'niveau_nappe_eau'
            titre_graphique = 'Niveau piézométrique'
            if self.type_graphique == 'scatter':
                legende = f'Niveau - {id_point}'
                self.nom_graphique = str(self.dataPlotlyDockwidget.idx) + ' Courbe ' + legende
            elif self.type_graphique == 'box':
                legende = 'Niveau'
                self.nom_graphique = str(self.dataPlotlyDockwidget.idx) + ' Boxplot ' + legende
        elif self.type_data == 'analyse':
            point_code = 'code_bss'
            x_time = 'date_debut_prelevement'
            y_data = 'resultat'
            titre_graphique = f'{self.nom_parametre} ({self.code_parametre})'
            if self.type_graphique == 'scatter':
                legende = f'{self.nom_parametre} - {id_point}'
                self.nom_graphique = str(self.dataPlotlyDockwidget.idx) + ' Courbe ' + legende
            elif self.type_graphique == 'box':
                legende = self.nom_parametre
                self.nom_graphique = str(self.dataPlotlyDockwidget.idx) + ' Boxplot ' + legende

        # Dictionnaires à remplir avec les paramètres et propriétés du graphique et de la mise en page
        plot_input_dic = {}
        plot_input_dic['plot_prop'] = {}
        plot_input_dic['layout_prop'] = {}

        # Paramètres principaux du graphique : type de graphique et couche
        plot_input_dic['plot_type'] = self.type_graphique
        plot_input_dic['layer'] = self.data_layer

        # Propriétés du graphique et de la mise en page en fonction du type de graphique

        if self.type_graphique == 'scatter':
            plot_input_dic['plot_prop']['x_name'] = x_time
            plot_input_dic['plot_prop']['y_name'] = y_data
            # Données x et y du graphique
            xx = [i[x_time] for i in self.data_layer.getFeatures(self.request)]
            yy = [i[y_data] for i in self.data_layer.getFeatures(self.request)]
            plot_input_dic['plot_prop']['x'] = xx
            plot_input_dic['plot_prop']['y'] = yy
            # Id des points pour l'interaction entre le graphique et la table attributaire
            ids = [i.id() for i in self.data_layer.getFeatures(self.request)]
            plot_input_dic['plot_prop']['featureIds'] = ids
            # Autres propriétés du graphique
            plot_input_dic['plot_prop']['marker_size'] = 7
            plot_input_dic['plot_prop']['marker'] = 'lines+markers'
            plot_input_dic['plot_prop']['name'] = legende
            # Active l'affichage de la légende du graphique
            plot_input_dic['layout_prop']['legend'] = True

        elif self.type_graphique == 'box':
            plot_input_dic['plot_prop']['x_name'] = point_code
            plot_input_dic['plot_prop']['y_name'] = y_data
            # Données x et y du graphique
            xx = [i[point_code] for i in self.data_layer.getFeatures(self.request)]
            yy = [i[y_data] for i in self.data_layer.getFeatures(self.request)]
            plot_input_dic['plot_prop']['x'] = xx
            plot_input_dic['plot_prop']['y'] = yy
            # Pour l'interaction entre le graphique et la table attributaire :
            # Id des box classés par la variable x de groupement + propriété 'custom' non commentée dans DataPlotly
            plot_input_dic['plot_prop']['featureBox'] = sorted(set(xx), key=xx.index)
            plot_input_dic['plot_prop']['custom'] = [point_code]
            # Affichage de statistiques supplémentaires sur les boxplots
            plot_input_dic['plot_prop']['box_outliers'] = 'suspectedoutliers'
            plot_input_dic['plot_prop']['box_stat'] = True
            plot_input_dic['plot_prop']['name'] = legende
            # Désactive l'affichage de la légende du graphique
            plot_input_dic['layout_prop']['legend'] = False

        # Propriétés générales de mise en page
        plot_input_dic['layout_prop']['title'] = titre_graphique
        plot_input_dic['layout_prop']['x_title'] = ''
        plot_input_dic['layout_prop']['y_title'] = ''
        plot_input_dic['layout_prop']['z_title'] = ''

        # Affichage sur l'interface de DataPlotly des paramètres et propriétés choisies ci-dessus
        # Type de graphique
        for k, v in self.dataPlotlyDockwidget.plot_types2.items():
            if self.dataPlotlyDockwidget.plot_types2[k] == plot_input_dic["plot_type"]:
                for ii, kk in enumerate(self.dataPlotlyDockwidget.plot_types.keys()):
                    if self.dataPlotlyDockwidget.plot_types[kk] == k:
                        self.dataPlotlyDockwidget.plot_combo.setItemIcon(ii, kk)
                        self.dataPlotlyDockwidget.plot_combo.setItemText(ii, k)
                        self.dataPlotlyDockwidget.plot_combo.setCurrentIndex(ii)
        # Couche, x, y, z
        try:
            self.dataPlotlyDockwidget.layer_combo.setLayer(plot_input_dic["layer"])
            if 'x_name' in plot_input_dic["plot_prop"] and plot_input_dic["plot_prop"]["x_name"]:
                self.dataPlotlyDockwidget.x_combo.setField(plot_input_dic["plot_prop"]["x_name"])
            if 'y_name' in plot_input_dic["plot_prop"] and plot_input_dic["plot_prop"]["y_name"]:
                self.dataPlotlyDockwidget.y_combo.setField(plot_input_dic["plot_prop"]["y_name"])
            if 'z_name' in plot_input_dic["plot_prop"] and plot_input_dic["plot_prop"]["z_name"]:
                self.dataPlotlyDockwidget.z_combo.setField(plot_input_dic["plot_prop"]["z_name"])
        except:
            pass

        # A faire : afficher sur l'interface les choix effectués pour les widgets ci-dessous
        # self.dataPlotlyDockwidget.marker_size   plot_input_dic['plot_prop']['marker_size']
        # self.dataPlotlyDockwidget.marker_type_combo    plot_input_dic['plot_prop']['marker']
        # self.dataPlotlyDockwidget.legend_title    plot_input_dic['plot_prop']['name']
        # self.dataPlotlyDockwidget.outliers_combo plot_input_dic['plot_prop']['box_outliers']
        # self.dataPlotlyDockwidget.box_statistic_combo  plot_input_dic['plot_prop']['box_stat']

        ##Pour référence, toutes les propriétés de graphique de DataPlotly
        # plot_properties = {
        #    'x':xx,
        #    'y':yy,
        #    'z':zz,
        #    # featureIds are the ID of each feature needed for the selection and zooming method
        #    'featureIds':getIds(self.layer_combo.currentLayer(), self.selected_feature_check.isChecked()),
        #    'featureBox':getSortedId(self.layer_combo.currentLayer(), xx),
        #    'custom':[self.x_combo.currentText()],
        #    'hover_text':self.info_hover[self.info_combo.currentText()],
        #    'additional_hover_text':QgsVectorLayerUtils.getValues(self.layer_combo.currentLayer(), self.additional_info_combo.currentText(), selectedOnly=self.selected_feature_check.isChecked())[0],
        #    'x_name':self.x_combo.currentText(),
        #    'y_name':self.y_combo.currentText(),
        #    'z_name':self.z_combo.currentText(),
        #    'in_color':self.in_color,
        #    'colorscale_in':self.col_scale[self.color_scale_data_defined_in.currentText()],
        #    'show_colorscale_legend':color_scale_visible,
        #    'invert_color_scale':self.color_scale_data_defined_in_invert_check.isChecked(),
        #    'out_color':hex_to_rgb(self.out_color_combo),
        #    'marker_width':self.marker_width.value(),
        #    'marker_size':self.marker_size_value,
        #    'marker_symbol':self.point_types2[self.point_combo.currentData()],
        #    'line_dash':self.line_types2[self.line_combo.currentText()],
        #    'box_orientation':self.orientation_box[self.orientation_combo.currentText()],
        #    'marker':self.marker_types[self.marker_type_combo.currentText()],
        #    'opacity':(100 - self.alpha_slid.value()) / 100.0,
        #    'box_stat':self.statistic_type[self.box_statistic_combo.currentText()],
        #    'box_outliers':self.outliers_dict[self.outliers_combo.currentText()],
        #    'name':self.legend_title.text(),
        #    'normalization':self.normalization[self.hist_norm_combo.currentText()],
        #    'cont_type':self.contour_type[self.contour_type_combo.currentText()],
        #    'color_scale':self.col_scale[self.color_scale_combo.currentText()],
        #    'show_lines':self.show_lines_check.isChecked(),
        #    'cumulative':self.cumulative_hist_check.isChecked(),
        #    'invert_hist':self.invert_hist,
        #    'bins':self.bin_val,
        #    'show_mean_line':self.showMeanCheck.isChecked(),
        #    'violin_side':self.violin_side[self.violinSideCombo.currentText()]
        # }

        ## Pour référence, toutes les propriétés de la mise en page
        # layout_properties = {
        #    'legend':self.show_legend_check.isChecked(),
        #    'legend_orientation':legend_or,
        #    'title':self.plot_title_line.text(),
        #    'x_title':self.x_axis_title.text(),
        #    'y_title':self.y_axis_title.text(),
        #    'z_title':self.z_axis_title.text(),
        #    'range_slider':dict(visible=self.range_slider_combo.isChecked(), borderwidth=1),
        #    'bar_mode':self.bar_modes[self.bar_mode_combo.currentText()],
        #    'x_type':self.x_axis_type[self.x_axis_mode_combo.currentText()],
        #    'y_type':self.y_axis_type[self.y_axis_mode_combo.currentText()],
        #    'x_inv':self.x_invert,
        #    'y_inv':self.y_invert,
        #    'bargaps':self.bar_gap.value()
        # }

        # Instanciation d'un objet Plot (classe Plot du module data_plotly_plot)
        self.plotobject = Plot(
            plot_input_dic['plot_type'],
            plot_input_dic['plot_prop'],
            plot_input_dic['layout_prop']
        )

        # initialize plot properties and build them
        self.plotobject.buildTrace()

        # Pour analyser le contenu de l'objet trace renvoyé par Plotly
        # trace = self.plotobject.trace

        # initialize layout properties and build them
        self.plotobject.buildLayout()

        # unique name for each plot trace (name is idx_plot, e.g. 1_scatter)
        self.dataPlotlyDockwidget.pid = ('{}_{}'.format(str(self.dataPlotlyDockwidget.idx), plot_input_dic["plot_type"]))

        # create default dictionary that contains all the plot and properties
        self.dataPlotlyDockwidget.plot_traces[self.dataPlotlyDockwidget.pid] = self.plotobject

        # Construit un dictionnaire des informations d'identification du graphique
        dict_graph = {"nom_groupe_couches": self.groupe_parent_point_layer.name(),
                      "id_couche_point": self.point_layer.id(),
                      "nom_parametre": self.nom_parametre,
                      "code_parametre": self.code_parametre,
                      "id_couche_data": self.data_layer.id(),
                      "type_data": self.type_data,
                      "pid_dataplotly": self.dataPlotlyDockwidget.pid,
                      "uid_plotly": ""} # sera défini plus bas après la création de la trace par Plotly

        # Ajoute un item dans le dictionnaire des graphiques
        # self.dict_graph_dataplotly[self.nom_graphique] = self.dataPlotlyDockwidget.pid
        self.dict_graph_dataplotly[self.nom_graphique] = dict_graph

        # Ajoute le nom du graphique au combobox de choix d'un graphique
        list_nom_graph = [self.graphDockwidget.cbx_choisirGraphiqueDataPlotly.itemText(i)
                          for i in range(self.graphDockwidget.cbx_choisirGraphiqueDataPlotly.count())]
        list_nom_graph.insert(1, self.nom_graphique)
        self.graphDockwidget.cbx_choisirGraphiqueDataPlotly.clear()
        self.graphDockwidget.cbx_choisirGraphiqueDataPlotly.addItems(list_nom_graph)

        # just add 1 to the index
        self.dataPlotlyDockwidget.idx += 1

        # enable the Update Button to allow the updating of the plot
        self.dataPlotlyDockwidget.update_btn.setEnabled(True)

        # Appel de la fonction équivalente à la fonction createPlot de la classe DataPlotlyDockWidget
        self.createPlotDataPlotly()


    def createPlotDataPlotly(self):
        """
        Fonction équivalente à la fonction createPlot de la classe DataPlotlyDockWidget
        qui permet de tracer un graphique sur la mise en page de DataPlotly
        """
        # set the correct index page of the widget
        self.dataPlotlyDockwidget.stackedPlotWidget.setCurrentIndex(1)
        # highlight the correct plot row in the listwidget
        self.dataPlotlyDockwidget.listWidget.setCurrentRow(2)

        # Effacement éventuel des graphiques précédents
        if self.ecraser_graphique == True:
            self.dataPlotlyDockwidget.clearPlotView()
            disposition_graphique = 'Empiler'
        else:
            disposition_graphique = self.graphDockwidget.cbx_choisirDispositionGraphe.currentText()

        # if self.dataPlotlyDockwidget.sub_dict[self.dataPlotlyDockwidget.subcombo.currentText()] == 'single':
        if disposition_graphique == 'Empiler':

            # plot single plot, check the object dictionary lenght
            if len(self.dataPlotlyDockwidget.plot_traces) <= 1:
                # Crée le code html correspondant au graphique
                self.plot_path = self.plotobject.buildFigure()

            # to plot many plots in the same figure
            else:
                # plot list ready to be called within go.Figure
                pl = []
                # layout list
                ll = None

                for k, v in self.dataPlotlyDockwidget.plot_traces.items():
                    pl.append(v.trace[0])
                    ll = v.layout

                # Crée le code html correspondant à la liste de graphiques (pl = plot list)
                self.plot_path = self.plotobject.buildFigures(self.type_graphique, pl)

        # choice to draw subplots instead depending on the combobox
        # elif self.dataPlotlyDockwidget.sub_dict[self.dataPlotlyDockwidget.subcombo.currentText()] == 'subplots':
        elif disposition_graphique != 'Empiler':

            gr = len(self.dataPlotlyDockwidget.plot_traces)
            pl = []
            tt = tuple([v.layout['title'] for v in self.dataPlotlyDockwidget.plot_traces.values()])

            for k, v in self.dataPlotlyDockwidget.plot_traces.items():
                pl.append(v.trace[0])

            # plot in single row and many columns
            # if self.dataPlotlyDockwidget.radio_rows.isChecked():
            if disposition_graphique == 'Juxtaposer en ligne':

                # Crée le code html correspondant à la liste de graphiques (pl = plot list)
                self.plot_path = self.plotobject.buildSubPlots('row', 1, gr, pl, tt)

            # plot in single column and many rows
            # elif self.dataPlotlyDockwidget.radio_columns.isChecked():
            elif disposition_graphique == 'Juxtaposer en colonne':

                # Crée le code html correspondant à la liste de graphiques (pl = plot list)
                self.plot_path = self.plotobject.buildSubPlots('col', gr, 1, pl, tt)

        # ===================================

        # Equivalent de la fonction refreshPlotView de la classe DataPlotlyDockWidget

        plot_url = QUrl.fromLocalFile(self.plot_path)
        self.dataPlotlyDockwidget.plot_view.load(plot_url)
        self.dataPlotlyDockwidget.layoutw.addWidget(self.dataPlotlyDockwidget.plot_view)
        self.dataPlotlyDockwidget.raw_plot_text.clear()
        with open(self.plot_path, 'r') as myfile:
            plot_text = myfile.read()
        self.dataPlotlyDockwidget.raw_plot_text.setPlainText(plot_text)

        # ===================================

        # A chaque appel des fonctions buildFigure, buildFigures ou buildSubPlots de DataPlotly,
        # donc à chaque appel de la fonction createPlotDataPlotly de PickEau, les uid de chaque trace
        # sont recréés par Plotly. On les recherche donc les nouveaux uid dans le texte html
        # nouvellement créé par Plotly et on les modifie dans le dict des graphiques PickEau

        # Capture du texte décrivant la mise en page
        match = re.search('Plotly.newPlot\((.*)\)', plot_text)
        # Ajout de crochets pour en faire un chaîne représentant une liste python
        substr = "[" + match.group(1) + "]"
        # Transformation de la str en liste de dict par json
        list_text_plot = json.loads(substr)
        # 1er élément = id Plotly du graphique, 2ème élément = liste des dict de graphique, etc.
        list_dict_plot = list_text_plot[1]
        # On parcourt simultanément le dict PickEau des infos sur les graphiques et la liste Plotly des dict de graphique
        for (nom_graph, dict_graph), dict_plot in zip(self.dict_graph_dataplotly.items(), list_dict_plot):
            # Ajout des uid dans le dict PickEau des graphiques (la correspondance est correcte
            # car depuis la version 3.6 de Python l'ordre d'ajout des items dans un dict est conservé !)
            dict_graph["uid_plotly"] = dict_plot["uid"]


    def effacer_graphique(self):
        """
        Fonction d'effacement d'un seul ou de tous les graphiques présents sur la mise en page DataPlotly
        """
        # Appel de la fonction de vérification du chargement des plugins
        self.verifier_chargement_plugins()
        # Affichage du dockwidget DataPlotly
        self.dataPlotlyDockwidget.show()
        # Mise au premier plan de l'onglet du dockwidget DataPlotly
        self.dataPlotlyDockwidget.raise_()

        # Obtient le nom du graphique à effacer
        nom_graphique_combobox = self.graphDockwidget.cbx_choisirGraphiqueDataPlotly.currentText()

        if nom_graphique_combobox == "Tous":
            # Effacement des graphiques existants
            self.dataPlotlyDockwidget.clearPlotView()
            # Réinitialise le compteur de graphiques
            self.dataPlotlyDockwidget.idx = 1
            # Vide la combobox des graphiques DataPlotly
            self.graphDockwidget.cbx_choisirGraphiqueDataPlotly.clear()
            self.graphDockwidget.cbx_choisirGraphiqueDataPlotly.addItems(["Tous"])
            # Vide le dictionnaire associé à la combobox des noms de graphiques DataPlotly
            self.dict_graph_dataplotly = {}
        else:
            # Obtient l'identifiant du graphique
            # pid_graphique = self.dict_graph_dataplotly[nom_graphique_combobox]
            pid_graphique = self.dict_graph_dataplotly[nom_graphique_combobox]["pid_dataplotly"]
            # Supprime l'item du dictionnaire associé à la combobox des noms de graphiques DataPlotly
            self.dict_graph_dataplotly.pop(nom_graphique_combobox)
            # Repeuple la combobox de choix d'un graphique
            self.graphDockwidget.cbx_choisirGraphiqueDataPlotly.clear()
            self.graphDockwidget.cbx_choisirGraphiqueDataPlotly.addItems(["Tous"])
            self.graphDockwidget.cbx_choisirGraphiqueDataPlotly.addItems(list(self.dict_graph_dataplotly.keys()))
            # Copie le dictionnaire des graphiques DataPlotly sans le graphique qu'on veut supprimer
            new_dict_plot_traces = {key: val for key, val in self.dataPlotlyDockwidget.plot_traces.items() if key != pid_graphique}
            # Efface la mise en page (ce qui a pour effet de vider le dictionnaire des graphiques DataPlotly)
            self.dataPlotlyDockwidget.clearPlotView()
            # Affecte le nouveau dictionnaire à la variable plot_traces
            self.dataPlotlyDockwidget.plot_traces = new_dict_plot_traces
            # S'il y a au moins un graphique restant dans le dictionnaire des graphiques DataPlotly en plus de "Tous"
            if len(self.dataPlotlyDockwidget.plot_traces) > 0:
                # Recrée l'ensemble des graphiques présents dans le dictionnaire en respectant la nouvelle mise en page choisie
                self.createPlotDataPlotly()
            else:
                # Réinitialise le compteur de graphiques
                self.dataPlotlyDockwidget.idx = 1


    # Fonction supprimée car génère un 'événement 'selectionChanged' qui est en interaction
    # non désirée avec l'événement 'selectionChanged' de la fonction 'selectionner_points_carte'

    # def activer_graphe_auto(self):
    #     """
    #     Fonction qui active / désactive la fonctionnalité de tracé automatique
    #     des graphiques dans DataPlotly, selon l'état de la case à cocher 'ckx_activerGrapheAuto'
    #     """
    #     if self.graphDockwidget.ckx_activerGrapheAuto.isChecked():
    #
    #         self.iface.mapCanvas().selectionChanged.connect(self.tracer_graphique_automatique)
    #         self.iface.messageBar().pushMessage("Le tracé AUTOMATIQUE des graphiques lors d'une sélection de point(s) sur la carte est ACTIF")
    #     else:
    #         self.iface.mapCanvas().selectionChanged.disconnect(self.tracer_graphique_automatique)
    #         self.iface.messageBar().pushMessage("Le tracé AUTOMATIQUE des graphiques lors d'une sélection de point(s) sur la carte n'est PAS ACTIF")


    # Fonction supprimée car s'active à l'émission d'un 'événement 'selectionChanged' qui est en interaction
    # non désirée avec l'événement 'selectionChanged' de la fonction 'selectionner_points_carte'

    # def tracer_graphique_automatique(self, point_layer):
    #     """
    #     Fonction qui s'exécute à la réception d'un signal de modification
    #     de la sélection des points sur la carte : le paramètre 'point_layer'
    #     est automatiquement passé à la fonction, il s'agit de la couche Qgis
    #     correspondant à un paramètre téléchargé par PickEau et dont
    #     les points sont sélectionnés.
    #     """
    #     # Couche dont les points sont sélectionnés
    #     self.point_layer = point_layer
    #
    #     # Appel de la fonction principale de tracé des graphiques
    #     self.tracer_graphique_main()

    # ==========================================================================
    # Fonctions d'affichage et de commentaire des données
    # ==========================================================================

    def afficher_data_table(self):
        """
        Affiche la table des données attributaires du groupe de couches de résultats PickEau actif
        (dont l'un des éléments est sélectionné :groupe de couche lui-même ou une des couche de points
        ou la table de données
        """
        # Initialisation au cas où une table précédente ait été supprimée (donc l'objet n'existe plus)
        self.attribute_dockwidget = None
        try:
            # Appel de la fonction de recherche de la table de données
            # du groupe de couches résultat qui est actif.
            self.rechercher_data_layer()

            # Définit la liste des widgets de l'application Qgis
            application_list_widgets = QApplication.instance().allWidgets()
            # Définit un filtre sur la liste des widgets de l'application Qgis
            list_widget_table = [w for w in application_list_widgets if self.data_layer.name() in w.objectName()]

            # Si un widget affichant la table n'existe pas déjà (donc si la table n'est pas déjà affichée)
            if len(list_widget_table) == 0:

                # Instancie la table attributaire de la couche de données
                self.attribute_dockwidget = self.iface.showAttributeTable(self.data_layer)

                # Définit la liste des objets enfants de la table attributaire :
                # permet de trouver les noms des objets correspondants à des actions possibles
                # list_children = [ch.objectName() for ch in attribute_dialog.children()]

                # Si la table attributaire existe (n'est pas None)
                if self.attribute_dockwidget:
                    # Connecte l'événement de fermeture de la table à la fonction de mise à jour de la combobox qui liste les tables affichées
                    self.attribute_dockwidget.destroyed.connect(self.mettre_a_jour_cbx_choisirTableData)
                    # Actionne le bouton 'intégrer la table attributaire'
                    self.attribute_dockwidget.findChild(QAction, 'mActionDockUndock').trigger()
                    # Ajoute le nom de la table de données au combobox de choix d'une table à commenter
                    list_nom_table = [self.graphDockwidget.cbx_choisirTableData.itemText(i) for i in range(self.graphDockwidget.cbx_choisirTableData.count())]
                    list_nom_table.insert(0, self.data_layer.name())
                    list_nom_table = list(set(list_nom_table))
                    self.graphDockwidget.cbx_choisirTableData.clear()
                    self.graphDockwidget.cbx_choisirTableData.addItems(list_nom_table)
                else:
                    raise ErreurTypeCouchePointSelectionnee

            else:
                self.iface.messageBar().pushMessage("La table de données est déjà affichée !",
                    Qgis.Warning)


        except ErreurTypeCouchePointSelectionnee:
            self.iface.messageBar().pushMessage("La couche de points sélectionnée n'est pas une couche de résultats créée par PickEau ! ",
                                                Qgis.Critical)


    def mettre_a_jour_cbx_choisirTableData(self, table_dockwidget):
        """
        Fonction de mise à jour de la combobox cbx_choisirTableData activée
        par l'événement de fermeture de l'objet dockwidget contenant une table attributaire
        """
        nom_table_dockwidget = table_dockwidget.objectName()
        list_nom_table_combobox = []
        for i in range(self.graphDockwidget.cbx_choisirTableData.count()):
            nom_table_combobox = self.graphDockwidget.cbx_choisirTableData.itemText(i)
            if nom_table_combobox.replace(".","_") not in nom_table_dockwidget:
                list_nom_table_combobox.append(nom_table_combobox)
        self.graphDockwidget.cbx_choisirTableData.clear()
        self.graphDockwidget.cbx_choisirTableData.addItems(list_nom_table_combobox)


    def commenter_selected_data_rows(self):
        """
        Fonction qui affecte un commentaire choisi par l'utilisateur aux lignes sélectionnées
        de la table de données choisie par l'utilisateur.
        """
        # Obtient le nom de la table de données modifiée à commenter
        data_layer_name = self.graphDockwidget.cbx_choisirTableData.currentText()
        if data_layer_name != '':
            # Instancie la table à commenter
            data_layer = QgsProject.instance().mapLayersByName(data_layer_name)[0]
            # Obtient la liste des lignes sélectionnées de la table
            iter_selected_rows = data_layer.getSelectedFeatures()
            # S'il y a au moins une ligne sélectionnée dans la table
            if isinstance(iter_selected_rows, QgsFeatureIterator) :
                # Obtient le type de commentaire
                commentaire = self.graphDockwidget.cbx_choisirTypeCommentaire.currentText()
                # Débute une session de modification d'attributs
                data_layer.startEditing()
                # Commence l'édition
                data_layer.beginEditCommand('Edit')
                # Boucle sur les lignes sélectionnées de la table
                for feature in iter_selected_rows:
                    # Affecte le commentaire choisi par l'utilisateur
                    data_layer.changeAttributeValue(feature.id(), data_layer.dataProvider().fieldNameIndex('commentaire'), commentaire)
                # Termine l'édition
                data_layer.endEditCommand()


    def enregistrer_commentaires(self):

        # Obtient le nom de la table de données modifiée à enregistrer
        data_layer_name = self.graphDockwidget.cbx_choisirTableData.currentText()
        if data_layer_name != '':
            # Instancie la table à commenter
            data_layer = QgsProject.instance().mapLayersByName(data_layer_name)[0]
            # Vérifie si la table de données est en mode édition
            if data_layer.isEditable():
                # Enregistre définitivement les changements dans la table
                data_layer.commitChanges()


    def annuler_commentaires(self):
        """
        Fonction qui permet d'annuler les modifications apportées aux commentaires
        de la table de données choisie par l'utilisateur
        """
        # Obtient le nom de la table de données modifiée qu'il faut sortir du mode édition
        data_layer_name = self.graphDockwidget.cbx_choisirTableData.currentText()
        if data_layer_name != '':
            # Instancie la table à commenter
            data_layer = QgsProject.instance().mapLayersByName(data_layer_name)[0]
            # Vérifie si la table de données est en mode édition
            if data_layer.isEditable():
                # Définit la liste des widgets de l'application Qgis
                application_list_widgets = QApplication.instance().allWidgets()
                # Définit un filtre sur la liste des widgets de l'application Qgis
                list_widget_table = [w for w in application_list_widgets if data_layer.name().replace('.','_') in w.objectName()]
                # Si un widget affichant la table existe (donc si la table est affichée)
                if len(list_widget_table) != 0:
                    # Instancie le widget table de la couche de données choisie
                    widget_table = list_widget_table[0]
                    # Actionne le bouton bascule pour sortir du mode édition
                    widget_table.findChild(QAction, 'mActionToggleEditing').trigger()
                else:
                    self.iface.messageBar().pushMessage("Veuillez afficher la table de données pour permettre la sortie du mode édition " +
                                                        "et pouvoir choisir d'annuler les modifications, ou faite-le manuellement par un clic-droit " +
                                                        "sur le nom de la couche puis 'Basculer en mode édition'",
                                                        Qgis.Warning)


    # def afficher_selected_data_rows(self):
    #     """
    #     Fonction qui active / désactive le filtre 'Ne montrer que les entités sélectionnées'
    #     de la dernière table attributaire affichée, selon l'état de la case à cocher 'ckx_afficherSelectedDataRows'
    #     """
    #     try:
    #         # Pour gérer le fait que la table attributaire des données peut ne pas être chargée
    #         if self.attribute_dockwidget:
    #             # Si la case à cocher 'ckx_afficherSelectedDataRows' est cochée
    #             if self.graphDockwidget.ckx_afficherSelectedDataRows.isChecked():
    #                 # Actionne le filtre 'Ne montrer que les entités sélectionnées'
    #                 self.attribute_dockwidget.findChild(QAction, 'mActionSelectedFilter').trigger()
    #             # Sinon
    #             else:
    #                 # Actionne le filtre 'Montrer toutes les entités'
    #                 self.attribute_dockwidget.findChild(QAction, 'mActionShowAllFilter').trigger()
    #     except:
    #         pass


    # ==========================================================================
    # Fonctions utilitaires
    # ==========================================================================

    def verifier_chargement_plugins(self):
        """
        Vérification du chargement des plugins DataPlotly et PickEau : chargement des plugings manquants
        et placement de tous les dockwidgets droits en onglet du plugin PickEau
        """
        tabifier = False

        # Vérifie si le plugin DataPlotly est lancé, sinon on le lance
        self.dataPlotlyDockwidget = self.iface.mainWindow().findChild(QDockWidget, 'DataPlotlyDockWidgetBase')
        if not self.dataPlotlyDockwidget:
            # Crée l'instance du plugin DataPlotly et le lance
            plugins['DataPlotly'].run()
            # Instanciation du dockwidget DataPlotly
            self.dataPlotlyDockwidget = self.iface.mainWindow().findChild(QDockWidget, 'DataPlotlyDockWidgetBase')
            # Activation du rafraîchissement automatique de la mise en page
            self.dataPlotlyDockwidget.live_update_check.setChecked(True)
            tabifier = True

        # Vérifie si le plugin PickEau est lancé, sinon on le lance après DataPlotly
        # (pour que l'ordre de connection des signaux du webview soit fait dans cet ordre)
        self.mainDockwidget = self.iface.mainWindow().findChild(QDockWidget, 'PickEauDockWidgetBase')
        # Sinon on le lance
        if not self.mainDockwidget:
            # Lance le plugin PickEau
            plugins['pickeau'].run()
            # Redéfinit l'instance du dockwidget
            self.mainDockwidget = self.iface.mainWindow().findChild(QDockWidget, 'PickEauDockWidgetBase')
            tabifier = True

        # Si l'un des deux plugins n'était pas lancé, on tabifie =
        # on place tous les dockwidgets affichés à droite en onglets de PickEau
        if tabifier == True:
            # Récupère l'emplacement du dockwidget PickEau
            main_dockwidget_area = self.iface.mainWindow().dockWidgetArea(self.mainDockwidget)
            # Mise en onglet de tous les QdockWidget
            list_dockwidgets = self.iface.mainWindow().findChildren(QDockWidget)
            # Boucle sur tous les dockwidgets
            for dwiget in list_dockwidgets:
                # Si le dockwidget n'est pas PickEau
                if dwiget is not self.mainDockwidget:
                    # Si le dockwidget est placé à droite et n'est pas caché
                    if self.iface.mainWindow().dockWidgetArea(dwiget) == main_dockwidget_area and dwiget.isHidden() == False:
                        # On le place en onglet de PickEau
                        self.iface.mainWindow().tabifyDockWidget(self.mainDockwidget, dwiget)
