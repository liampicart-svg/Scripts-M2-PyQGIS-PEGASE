# -*- coding: utf-8 -*-
import os
import re
import processing
from datetime import datetime

try:
    from dateutil import parser
except ImportError:
    parser = None

from qgis.core import (QgsProject, QgsVectorLayer, QgsMapLayer, QgsRasterLayer, QgsVectorFileWriter)
from qgis.analysis import QgsZonalStatistics
from qgis.PyQt.QtWidgets import QMessageBox

#%% configuration des couches et repertoires
# appel du maillage vectoriel dedie aux 5 zones d etude de pegase
nom_couche_maillage = "4 - Maillage pour l'analyse des PEGASES (5 zones)"
nom_du_groupe_rasters = "Bathymétries adapted au maillage"
dossier_resultat = r"C:\Liam\QGIS\PEGASE_Projet_Liam\Comparaison\Analyse PEGASE\Excel_maillage_cube"
nom_fichier_csv = "VARIATIONS_ELEVATION_MAILLAGE-CHRONO_PEGASE3_c0.csv"

# calendrier des leves valides pour construire la chronique temporelle
dates_valides = ["2009", "2011", "2014", "2015", "2020", "2021", "2022", "2024", "2025", "2026"]

#%% fonction de decodage robuste des dates
def extract_date_robust(name):
    # normalise le format de la chaine de caracteres pour eviter les bugs d underscore
    cleaned = name.replace('_', '/').replace('-', '/')
    parts = re.findall(r'\d+', cleaned)
    if len(parts) >= 3:
        # extraction si le nom commence par l annee (aaaa/mm/jj)
        if int(parts[0]) > 2000:
            return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
        # extraction si le nom commence par le jour (jj/mm/aaaa)
        else:
            return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
    elif len(parts) == 1 and len(parts[0]) == 4:
        # repli sur le 1er janvier si seule l annee brute est lue
        return datetime(int(parts[0]), 1, 1)
    return None

#%% moteur de calcul chronologique pas-a-pas
def run_extraction_chronologique():
    print("--- DÉMARRAGE EXTRACTION CHRONOLOGIQUE ---")
    
    root = QgsProject.instance().layerTreeRoot()
    groupe_r = root.findGroup(nom_du_groupe_rasters)
    if not groupe_r:
        print("Groupe non trouvé")
        return

    # recuperation des mnt presents dans le volet qgis
    layers_raw = [l.layer() for l in groupe_r.children() if l.layer().type() == QgsMapLayer.RasterLayer]
    layers_dt = []
    
    for lyr in layers_raw:
        dt = extract_date_robust(lyr.name())
        if dt:
            layers_dt.append((dt, lyr))

    # tri chronologique absolu pour garantir le chaînage des calculs
    layers_dt.sort(key=lambda x: x[0])

    layers_m = QgsProject.instance().mapLayersByName(nom_couche_maillage)
    # correction geometrique et clonage en memoire vive pour ne pas corrompre le fichier shapefile d origine
    layer_maille = processing.run("native:fixgeometries", {'INPUT': layers_m[0], 'OUTPUT': 'memory:'})['OUTPUT']

    # boucle de calcul sequentielle : calcule l evolution entre chaque pas de temps successif (T_i moins T_i-1)
    for i in range(1, len(layers_dt)):
        l_a = layers_dt[i-1][1]  # mnt de reference (ancien)
        l_r = layers_dt[i][1]    # mnt de comparaison (recent)
        
        # nommage de la colonne qui servira de balise pour pandas (ex: mnt_a vs mnt_b)
        nom_colonne = f"{l_a.name()} vs {l_r.name()}"
        print(f"Calcul : {nom_colonne}")

        # ecriture de la formule algebrique transmise a la calculatrice raster de gdal
        formula = f"\"{l_r.name()}@1\" - \"{l_a.name()}@1\""
        
        res_calc = processing.run("qgis:rastercalculator", {
            'EXPRESSION': formula, 
            'LAYERS': [l_r, l_a],
            'CELLSIZE': 0, 
            'EXTENT': layer_maille.extent(), 
            'CRS': layer_maille.crs(),
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })
        
        # stockage virtuel du raster differentiel cree
        lyr_diff = QgsRasterLayer(res_calc['OUTPUT'], "temp", "gdal")
        
        # extraction des statistiques de zone : calcule la variation moyenne par polygone (maille)
        # qgis injecte d office le suffixe '_mean' au nom de colonne specifie ici
        QgsZonalStatistics(layer_maille, lyr_diff, nom_colonne, 1, QgsZonalStatistics.Mean).calculateStatistics(None)

#%% export vectoriel et reformatage du csv
    chemin_csv = os.path.join(dossier_resultat, nom_fichier_csv)
    # ecriture physique du csv avec separateur point-virgule et stockage de la geometrie au format wkt
    QgsVectorFileWriter.writeAsVectorFormat(layer_maille, chemin_csv, "utf-8", layer_maille.crs(), "CSV", 
                                            layerOptions=['GEOMETRY=AS_WKT', 'SEPARATOR=SEMICOLON'])

    # relecture immediate du fichier csv cree pour purger les scories de texte generees par qgis
    if os.path.exists(chemin_csv):
        with open(chemin_csv, 'r', encoding='utf-8') as f:
            texte = f.read()
        
        # suppression radicale des extensions '_mean' ou 'mean' pour coller exactement aux en-tetes attendus par pandas
        nouveau_texte = texte.replace('_mean', '').replace('mean', '')
        
        # reecriture finale et securisee du fichier texte final
        with open(chemin_csv, 'w', encoding='utf-8') as f:
            f.write(nouveau_texte)

    QMessageBox.information(None, "Succès", "Calcul terminé et exports nettoyés !")

# declenchement de la routine dans la console python de qgis
run_extraction_chronologique()