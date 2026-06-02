# -*- coding: utf-8 -*-
import os
import re
import processing
from datetime import datetime
from qgis.core import (QgsProject, QgsVectorLayer, QgsMapLayer, QgsRasterLayer, QgsVectorFileWriter)
from qgis.analysis import QgsZonalStatistics
from qgis.PyQt.QtWidgets import QMessageBox

#%% configuration
# appel de la couche du maillage + zones
nom_couche_maillage = "4 - Maillage pour l'analyse des brise-lames (6 zones)" 
# appel du groupe avec les bathymetries dans l arbre des couches
nom_du_groupe_rasters = "Bathymétries sans masque" 
# rangement du fichier cree
dossier_resultat = r"C:\Liam\QGIS\PEGASE_Projet_Liam\Comparaison\Brise-lames\Excel_maillage_cube" 
nom_fichier_csv = "VARIATIONS_ELEVATION_MAILLAGE-MATRICE_COMPLETE_Brise-lames_6z.csv" 

# dates valides pour filtrer les rasters qui nous interessent dans le groupe
dates_valides = ["2009", "2011", "2014", "2015", "2020"]

#%% fonctions de décodage des dates
def extract_date(name):
    # cherche une date complete type aaaa_mm_jj dans le nom du raster
    match = re.search(r'(\d{4})_(\d{2})_(\d{2})', name)
    if not match:
        # sinon cherche juste l annee sur 4 chiffres
        match = re.search(r'(\d{4})', name)
    if match and "_" in match.group(0):
        return datetime.strptime(match.group(0), '%Y_%m_%d')
    elif match:
        return datetime(int(match.group(0)), 1, 1)
    return None

#%% moteur d extraction et de calcul dOD
def run_extraction_compatible_python():
    print("--- DÉMARRAGE EXTRACTION (FORMAT COMPATIBLE PYTHON) ---")
    if not os.path.exists(dossier_resultat): os.makedirs(dossier_resultat)

    # 1. recuperation du maillage dans le projet qgis actif
    layers = QgsProject.instance().mapLayersByName(nom_couche_maillage)
    if not layers:
        QMessageBox.critical(None, "Erreur", f"Couche '{nom_couche_maillage}' non trouvée.")
        return
    
    # reparation des geometries au vol et creation d une couche temporaire en memoire cache
    layer_maille = processing.run("native:fixgeometries", {'INPUT': layers[0], 'OUTPUT': 'memory:'})['OUTPUT']

    # exploration de l arbre des couches pour choper le dossier des rasters
    root = QgsProject.instance().layerTreeRoot()
    groupe_r = root.findGroup(nom_du_groupe_rasters)
    
    # 2. tri et filtrage chrono des MNT presents dans le groupe
    layers_raw = [l.layer() for l in groupe_r.children() if l.layer().type() == QgsMapLayer.RasterLayer]
    layers_dt = []
    for lyr in layers_raw:
        dt = extract_date(lyr.name())
        if dt and any(v in lyr.name() for v in dates_valides):
            layers_dt.append((dt, lyr))
    
    # tri du plus ancien au plus recent
    layers_dt.sort(key=lambda x: x[0])

    # 3. boucles d intersection et calcul de la calculatrice raster
    idx = 1
    for i in range(len(layers_dt)):
        for j in range(i + 1, len(layers_dt)):
            l_a = layers_dt[i][1]
            l_r = layers_dt[j][1]
            
            # formatage du nom de la future colonne (ex: mnt1 vs mnt2)
            nom_colonne = f"{l_a.name()} vs {l_r.name()}"
            print(f"Calcul matrice : {nom_colonne}")

            # soustraction raster : mnt recent - mnt ancien (bande 1 @1)
            formula = f"\"{l_r.name()}@1\" - \"{l_a.name()}@1\""
            
            res_calc = processing.run("qgis:rastercalculator", {
                'EXPRESSION': formula,
                'LAYERS': [l_r, l_a],
                'CELLSIZE': 0, #calcul des pixels dans le cube 
                'EXTENT': layer_maille.extent(), 
                'CRS': layer_maille.crs(),
                'OUTPUT': 'TEMPORARY_OUTPUT'
            })
            
            # chargement du mnt differentiel temporaire en memoire virtualisee via gdal
            lyr_diff = QgsRasterLayer(res_calc['OUTPUT'], "temp", "gdal")

            # statistiques de zone : calcule la moyenne des pixels du mnt diff pour chaque carre de maillage
            zone_stats = QgsZonalStatistics(layer_maille, lyr_diff, nom_colonne, 1, QgsZonalStatistics.Mean)
            zone_stats.calculateStatistics(None)
            idx += 1

#%% export et nettoyage final du csv
    chemin_csv = os.path.join(dossier_resultat, nom_fichier_csv)
    
    # export de la couche de mailles modifiee au format csv standard avec geometries en wkt
    QgsVectorFileWriter.writeAsVectorFormat(layer_maille, chemin_csv, "utf-8", layer_maille.crs(), "CSV", layerOptions=['GEOMETRY=AS_WKT', 'SEPARATOR=SEMICOLON'])

    # relecture immediate du csv genere pour virer les suffixes automatiques de qgis
    with open(chemin_csv, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # qgis ajoute toujours _mean apres les stats de zone, on l efface pour pas bloquer les scripts de graphiques
    content = content.replace('_mean', '')
    
    # reecriture propre du fichier texte final
    with open(chemin_csv, 'w', encoding='utf-8-sig') as f:
        f.write(content)

    QMessageBox.information(None, "Succès", "Matrice compatible Python générée !")

# execution de la fonction principale dans la console qgis
run_extraction_compatible_python()