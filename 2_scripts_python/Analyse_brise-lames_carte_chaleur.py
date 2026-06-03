# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 09:13:39 2026

@author: l.picart
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import numpy as np
import re
import os
from datetime import datetime
import matplotlib.patheffects as path_effects

#%% configuration
SEUIL_DETECTION = 0.05
surface_maille = 99.878 

PATH_EXCEL = r"C:\Liam\QGIS\PEGASE_Projet_Liam\Comparaison\Brise-lames\Excel_maillage_cube\VARIATIONS_ELEVATION_MAILLAGE-MATRICE_COMPLETE_Brise-lames.csv"

# codes couleurs de la zone 1 a 5
COULEURS_ZONES_LISTE = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9465bd', '#0ad4fc']

def extract_centroid(wkt):
    # calcul des x et y au centre de la géométrie wkt
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(wkt))
    if len(nums) >= 2:
        x_coords = [float(nums[i]) for i in range(0, len(nums), 2)]
        y_coords = [float(nums[i]) for i in range(1, len(nums), 2)]
        return sum(x_coords)/len(x_coords), sum(y_coords)/len(y_coords)
    return None, None

def nettoyer_date(texte_brut):
    # nettoyage des chaines pour avoir un format de date propre
    match = re.search(r'(\d{4})_(\d{2})_(\d{2})', texte_brut)
    if match:
        jour, mois, annee = match.groups()
        return f"{jour}/{mois}/{annee}"
    return texte_brut

def formater_periode_titre(nom_colonne):
    # generation du titre de la periode pour les graphiques
    if " vs " in nom_colonne:
        parts = nom_colonne.split(" vs ")
        d_ancienne = nettoyer_date(parts[0])
        d_recente = nettoyer_date(parts[1])
        return f"{d_ancienne} au {d_recente}"
    return nom_colonne

#%% chargement et calculs statistiques
if os.path.exists(PATH_EXCEL):
    df = pd.read_csv(PATH_EXCEL, sep=';')
    
    # dictionnaire de correspondance des periodes cles du site
    periodes_cibles = {
        '2009/09/07 vs 2011/10/03': "État Initial (avant l'installation des brise-lames) \n Différentiel : 07/09/2009 - 03/10/2011",
        '2011/10/03 vs 2014/10/31': "Installation des brise-lames \n Différentiel : 03/10/2011 - 31/10/2014",
        '2014/10/31 vs 2015/09/11': "Suivi Post-installation \n Différentiel : 31/10/2014 - 11/09/2015",
        '2015/09/11 vs 2020/09/29': "Évolution Morphologique Long Terme \n Différentiel : 11/09/2015 - 29/09/2020"
    }

    # filtrage des colonnes valides
    colonnes_dispo = [c for c in periodes_cibles.keys() if c in df.columns]

    print("\n--- ANALYSEUR DE PÉRIODES CLÉS ---")
    for i, col in enumerate(colonnes_dispo):
        print(f"{i+1}. {periodes_cibles[col]} ({col})")

    choix = input("\nTapez le NUMÉRO de la période à analyser : ")
    idx = int(choix) - 1
    col_choisie = colonnes_dispo[idx]
    periode_label = periodes_cibles[col_choisie]

    df[['X', 'Y']] = df['WKT'].apply(lambda x: pd.Series(extract_centroid(x)))

    # boucle de calcul volumetrique zone par zone
    zones_stats = []
    for nom_zone, data_zone in df.groupby('Num'):
        data_valid = data_zone.dropna(subset=[col_choisie])
        surf_z = len(data_valid) * surface_maille
        gains = (data_valid[data_valid[col_choisie] >= SEUIL_DETECTION][col_choisie] * surface_maille).sum()
        pertes = (data_valid[data_valid[col_choisie] <= -SEUIL_DETECTION][col_choisie] * surface_maille).sum()
        net = gains + pertes
        dz = (net / surf_z) * 100 if surf_z > 0 else 0
        zones_stats.append({'zone': int(nom_zone), 'surface': surf_z, 'gains': gains, 'pertes': pertes, 'net': net, 'dz': dz})

#%% generation des figures cartographiques
    fig_maps, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), facecolor='white')

    # calcul de l emprise spatiale exacte pour eliminer les marges blanches
    padding = 5  
    xmin, xmax = df["X"].min() - padding, df["X"].max() + padding
    ymin, ymax = df["Y"].min() - padding, df["Y"].max() + padding

    # premier sous-graphique : carte thermique de variation d altitude
    ax1.set_facecolor('#C0C0C0')  
    norm_diff = TwoSlopeNorm(vmin=-2, vcenter=0, vmax=2)
    cmap_diff = plt.cm.RdBu

    for _, row in df.iterrows():
        val = row[col_choisie]
        if pd.isna(val): continue
        # filtrage des variations inferieures a 5cm
        c = '#FFFFFF' if abs(val) < SEUIL_DETECTION else cmap_diff(norm_diff(val))
        ax1.add_patch(Rectangle((row["X"]-5, row["Y"]-5), 10, 10, facecolor=c, edgecolor='none', zorder=2))

    ax1.set_aspect('equal')
    ax1.set_xlim(xmin, xmax)
    ax1.set_ylim(ymin, ymax)

    ax1.set_title(f"Différentiel altimétrique : {periode_label}\n(Blanc = Stable < {int(SEUIL_DETECTION*100)}cm - gris = masque)", 
                  fontweight="bold", fontsize=18, pad=10)

    # configuration de la barre de couleur et de ses legendes
    sm = plt.cm.ScalarMappable(norm=norm_diff, cmap=cmap_diff)
    cbar = fig_maps.colorbar(sm, ax=ax1, fraction=0.02, pad=0.02)
    cbar.set_label("Variation d'élévation (m)", fontweight='bold')
    cbar.outline.set_visible(False) 
    
    cbar.ax.text(3.0, 1.2, 'ACCRÉTION', va='center', ha='left', fontweight='bold', color='#053061')
    cbar.ax.text(4.4, 0.0, 'STABLE', va='center', ha='left', fontweight='bold', color='black')
    cbar.ax.text(3.0, -1.2, 'ÉROSION', va='center', ha='left', fontweight='bold', color='#67001f')

    # second sous-graphique : carte d identification des cellules de suivi
    ax2.set_facecolor('white') 
    zones_uniques = sorted(df['Num'].dropna().unique())
    color_map_zones = {zone: COULEURS_ZONES_LISTE[int(i) % len(COULEURS_ZONES_LISTE)] for i, zone in enumerate(zones_uniques)}

    for _, row in df.iterrows():
        z = row['Num']
        if pd.isna(z): continue
        c = color_map_zones[z]
        ax2.add_patch(Rectangle((row["X"]-5, row["Y"]-5), 10, 10, 
                                facecolor=c, edgecolor='white', linewidth=0.1, alpha=0.9, zorder=2))

    # placement du numero au centre de gravite de chaque zone
    for nom_zone, data_zone in df.groupby('Num'):
        if pd.isna(nom_zone): continue
        cx, cy = data_zone['X'].mean(), data_zone['Y'].mean()
        txt = ax2.text(cx, cy, f"{int(nom_zone)}", color='white', fontsize=14, fontweight='bold', ha='center', va='center', zorder=3)
        txt.set_path_effects([path_effects.withStroke(linewidth=3, foreground='black')])

    ax2.set_aspect('equal')
    ax2.set_xlim(xmin, xmax)
    ax2.set_ylim(ymin, ymax)
    ax2.set_title("LOCALISATION DES ZONES D'ÉTUDE", fontweight="bold", fontsize=14, pad=10)

    legend_elements = [Line2D([0], [0], marker='s', color='w', label=f'Zone {int(z)}',
                               markerfacecolor=color_map_zones[z], markersize=10, linestyle='None') for z in zones_uniques]
    ax2.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.02, 0.5), title="Légende Zones")

    plt.tight_layout()

#%% generation du tableau des bilans sedimentaires
    fig_table, ax3 = plt.subplots(figsize=(12, 6), facecolor='white')
    ax3.axis('off')

    columns = ['ZONE', 'SURFACE (m²)', 'GAINS (m³)', 'PERTES (m³)', 'NET (m³)', 'ΔZ MOY (cm)']
    data_table = []
    cell_colors = []

    # calcul de la ligne des sommets generaux
    total_surf = sum(s['surface'] for s in zones_stats)
    total_gains = sum(s['gains'] for s in zones_stats)
    total_pertes = sum(s['pertes'] for s in zones_stats)
    total_net = sum(s['net'] for s in zones_stats)
    total_dz = (total_net / total_surf) * 100 if total_surf > 0 else 0

    for s in zones_stats:
        row = [
            f"Zone {s['zone']}",
            f"{s['surface']:.1f}",
            f"{s['gains']:.1f}",
            f"{s['pertes']:.1f}",
            f"{s['net']:.1f}",
            f"{s['dz']:.2f}"
        ]
        data_table.append(row)
        
        # coloration automatique des lignes selon le signe algebraique du bilan net
        color_dz = '#b3cde3' if s['dz'] > 0 else '#fbb4ae' if s['dz'] < 0 else 'white'
        row_colors = [color_map_zones[s['zone']], 'white', 'white', 'white', 'white', color_dz]
        cell_colors.append(row_colors)

    data_table.append(['TOTAL', f"{total_surf:.1f}", f"{total_gains:.1f}", f"{total_pertes:.1f}", f"{total_net:.1f}", f"{total_dz:.2f}"])
    color_total_dz = '#b3cde3' if total_dz > 0 else '#fbb4ae' if total_dz < 0 else '#d3d3d3'
    cell_colors.append(['#d3d3d3', '#d3d3d3', '#d3d3d3', '#d3d3d3', '#d3d3d3', color_total_dz])

    table = ax3.table(cellText=data_table, colLabels=columns, cellColours=cell_colors, loc='center', cellLoc='center')
    
    table.auto_set_font_size(False)
    table.set_fontsize(15) 
    table.scale(1.2, 2.5)

    # application des styles de police sur les entetes et les totaux
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor('#444444')
            cell.get_text().set_color('white')
            cell.get_text().set_weight('bold')
        elif row > 0 and col == 0 and row <= len(zones_stats):
            cell.get_text().set_color('white')
            cell.get_text().set_weight('bold')
        elif row > 0 and col == 5:
            cell.get_text().set_weight('bold')

    ax3.set_title(f"Bilans sédimentaires - {periode_label}", fontweight="bold", fontsize=16, pad=0)
    plt.show()

else:
    print(f" Fichier introuvable : {PATH_EXCEL}")
