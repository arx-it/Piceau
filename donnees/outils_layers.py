import os
from datetime import datetime
from qgis.core import QgsVectorLayer, QgsVectorFileWriter


class OutilsLayers():

    @staticmethod
    def get_chemin_dossier_geopackage_depuis_couche(couche_courante: QgsVectorLayer):
        chemin_fichier_geopackage = OutilsLayers.get_chemin_fichier_geopackage(couche_courante)
        if (chemin_fichier_geopackage):
            chemin_dossier_geopackage = OutilsLayers.get_chemin_dossier_geopackage(chemin_fichier_geopackage)
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
    def creation_dossier_geopackage(chemin_geopackage: str, nom_dossier: str) -> str:
        horodate_resultat = datetime.now().strftime('%y%m%d%H%M%S')
        nom_dossier = nom_dossier + "_" + horodate_resultat
        dossier_a_creer = os.path.join(chemin_geopackage, nom_dossier)
        os.mkdir(dossier_a_creer)
        return dossier_a_creer

    # ATTENTION fait doublons avec la fonction présente dans pick_page_donnee.py. A remplacer dans le fichier page donnee
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
        # if ajouter_couche == True:
        #     options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        QgsVectorFileWriter.writeAsVectorFormat(qgs_vector_layer, chemin_geopackage, options)
