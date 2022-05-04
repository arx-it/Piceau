import os
from osgeo import ogr
from datetime import datetime
from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter, QgsLayerTreeGroup


class UtilitaireCouches():

    @staticmethod
    def get_chemin_dossier_geopackage_depuis_couche(couche_courante: QgsVectorLayer):
        chemin_fichier_geopackage = UtilitaireCouches.get_chemin_fichier_geopackage(couche_courante)
        if (chemin_fichier_geopackage):
            chemin_dossier_geopackage = UtilitaireCouches.get_chemin_dossier_geopackage(chemin_fichier_geopackage)
            return chemin_dossier_geopackage
        else:
            None

    # Détermination du chemin du geopackage auquel appartient la couche courante
    @staticmethod
    def get_chemin_fichier_geopackage(couche_courante: QgsVectorLayer) -> str:
        """
        Obtenir le chemin où est enregistré un layer

        :param chemin_fichier_geopackage: Couche dont on recherche le chemin
        :type chemin_fichier_geopackage: QgsVectorLayer

        :return: url dossier
        :rtype: str
        """

        chemin_fichier_geopackage = couche_courante.source().split("|")[0]
        if not os.path.isfile(chemin_fichier_geopackage):
            return None
        else:
            return chemin_fichier_geopackage

    @staticmethod
    def get_chemin_dossier_geopackage(chemin_fichier_geopackage: str) -> str:
        """
        Obtenir le chemin du dossier geopackage

        :param chemin_fichier_geopackage: chemin d'un fichier
        :type chemin_fichier_geopackage: str

        :return: url dossier
        :rtype: str
        """
        # Détermination du chemin du dossier contenant le geopackage auquel appartient la couche courante
        chemin_dossier_geopackage = os.path.dirname(chemin_fichier_geopackage)
        if not os.path.isdir(chemin_dossier_geopackage):
            return None
        else:
            return chemin_dossier_geopackage

    @staticmethod
    def creation_dossier_geopackage(chemin_geopackage: str, nom_dossier: str) -> dict:
        horodate_resultat = datetime.now().strftime('%y%m%d%H%M%S')
        nom_dossier = nom_dossier + "_" + horodate_resultat
        dossier_a_creer = os.path.join(chemin_geopackage, nom_dossier)
        os.mkdir(dossier_a_creer)
        dossiers = {
            "nomDossierCree": nom_dossier,
            "cheminDossierCree": dossier_a_creer
        }
        return dossiers

    # TODO --> fait doublons avec la fonction présente dans pick_page_donnee.py. A remplacer dans le fichier page donnee
    @staticmethod
    def ecrire_couche_geopackage(chemin_geopackage: str,
                                 qgs_vector_layer: QgsVectorLayer,
                                 layer_name: str,
                                 nom_fichier: str,
                                 epsg_origine="",
                                 epsg_destination="",
                                 ajouter_couche=False):
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

        features = qgs_vector_layer.getFeatures()
        # for feature in features:
        #     print("Feature ID: ", feature.id())

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = layer_name
        options.fileEncoding = "utf-8"
        chemin_geopackage = chemin_geopackage + "/" + nom_fichier

        # if (epsg_origine != "") and (epsg_destination != ""):
        #     transform_proj = QgsCoordinateTransform(QgsCoordinateReferenceSystem(epsg_origine),
        #                                             QgsCoordinateReferenceSystem(epsg_destination),
        #                                             QgsProject.instance())
        #     options.ct = transform_proj
        if ajouter_couche is True:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        error = QgsVectorFileWriter.writeAsVectorFormat(qgs_vector_layer, chemin_geopackage, options)
        if error[0] == QgsVectorFileWriter.NoError:
            print("success!")
        else:
            print(error)

    # TODO --> fait doublons avec la fonction présente dans pick_page_donnee.py. A remplacer dans le fichier page donnee
    @staticmethod
    def lire_toutes_couches_geopackage(chemin_geopackage: str,
                                       qgs_layer_tree_group: QgsLayerTreeGroup,
                                       developper_groupe=False):
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
                self._iface.messageBar().pushWarning("Impossible d'afficher la couche " + layer.GetName(), "Echec de l'affichage de la couche")
            QgsProject.instance().addMapLayer(gpkg_layer, False)
            layer_node = qgs_layer_tree_group.addLayer(gpkg_layer)
            if developper_groupe is True:
                layer_node.setExpanded(True)
            else:
                layer_node.setExpanded(False)
