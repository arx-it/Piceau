from qgis.core import QgsVectorLayer, QgsFeature


class DonneeApi():

    _listChamps: list
    _valeurs: list
    _nomTable: str

    def __init__(self, liste_champs: list, valeurs: list, nom_table: str):
        # self._list_champs = []
        self._listChamps = liste_champs
        self._valeurs = valeurs
        self._nomTable = nom_table

    def creationTable(self) -> QgsVectorLayer:
        """
        Créé une "table vecteur" depuis une liste de champs (QGisField) et des listes de valeurs

        :param champs: List de champs. C'est un tableau de QgsField
        :type champs: list

        :param values: List de valeurs. C'est une dictionnaire avec un id de stations puis un tableau des valeurs [val1, val2....]
        :type champs: dict

        :param stationIds: List des identifiants des stations (retourné par l'api piceau)
        :type stationIds: list

        :param tableName: non de la table créé
        :type tableName: string

        :return: table des données
        :rtype: QgsVectorLayer
        """
        uri = "None"
        table = QgsVectorLayer(uri, self._nomTable, "memory")
        dp = table.dataProvider()
        dp.addAttributes(self._listChamps)
        table.updateFields()
        fet = QgsFeature()
        for valeurs in self._valeurs:
            fet.setAttributes(valeurs)
            dp.addFeatures([fet])
        return table
