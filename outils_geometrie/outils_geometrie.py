from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform


class OutilsGeometrie():

    @staticmethod
    def genererTransformer(epsgDestination: int):
        """
        :param epsgDestination: Code EPSG vers lequel reprojeter
        :type epsgDestination: str

        :return: retourne un coordinate transform
        :rtype: QgsCoordinateTransform
        """

        # obtenir le crs du projet
        project = QgsProject.instance()
        epsgSource = project.crs().postgisSrid()
        projSource = QgsCoordinateReferenceSystem(epsgSource)
        projDest = QgsCoordinateReferenceSystem(epsgDestination)
        # transformation des coordonnées
        transformer = QgsCoordinateTransform(projSource, projDest, project)

        return transformer
