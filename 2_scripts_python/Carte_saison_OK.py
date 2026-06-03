# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 11:34:17 2026

@author: l.picart
"""

# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Rectangle
import numpy as np
import re
import os
from scipy.stats import norm

#%% configuration
SEUIL_DETECTION = 0.05
LIMITE_X = 736480
surface_maille = 99.878 

PATH_CSV = r"C:\Liam\QGIS\PEGASE_Projet_Liam\Comparaison\Saison\Excel_maillage_cube\VARIATIONS_ELEVATION_MAILLAGE-MATRICE_COMPLETE_Zone_Nord_c0.csv"

# configs pour les subplots des cartes
config_saisons = [
    {"col_name": "25/06/2024 vs 28/11/2024", "label": "Juin 2024 - Novembre 2024"},
    {"col_name": "28/11/2024 vs 30/06/2025", "label": "Novembre 2024 - Juin 2025"}
]

config_annuel = [
    {"col_name": "25/06/2024 vs 30/06/2025", "label": "Juin 2024 - Juin 2025 (Bilan annuel)"},
    {"col_name": "31/10/2014 vs 11/09/2015", "label": "Octobre 2014 - Septembre 2015 (Bilan annuel historique)"}
]

periodes_totales = config_saisons + config_annuel

#%% fonctions de calcul

def extract_centroid(wkt):
    # extrait x et y du texte géométrique wkt
    nums = re.findall(r"[-+]?\d*\.?\d+", str(wkt))
    if len(nums) >= 2:
        x_coords = [float(nums[i]) for i in range(0, len(nums), 2)]
        y_coords = [float(nums[i]) for i in range(1, len(nums), 2)]
        return sum(x_coords)/len(x_coords), sum(y_coords)/len(y_coords)
    return None, None

def calculer_stats(data, col):
    # tri des valeurs et calcul des volumes avec le seuil des 5cm
    data_v = data.dropna(subset=[col])
    v = data_v[col]
    surf = len(data_v) * surface_maille
    gains = (v[v >= SEUIL_DETECTION] * surface_maille).sum()
    pertes = (v[v <= -SEUIL_DETECTION] * surface_maille).sum()
    net = gains + pertes
    dz = (net / surf) * 100 if surf > 0 else 0
    # calcul du taux de fiabilité selon le bruit de mesure
    v_brasse = (v.abs() * surface_maille).sum()
    v_incert = surf * SEUIL_DETECTION
    fiab = (1 - (v_incert / v_brasse)) * 100 if v_brasse > v_incert else 0
    return {
        "bilan": [f"{surf:.1f}", f"+{gains:.1f}", f"{pertes:.1f}", f"{net:+.1f}", f"{dz:+.2f}"],
        "fiab": [f"{v_incert:.1f}", f"{v_brasse:.1f}", f"{fiab:.2f} %"],
        "val_net": net 
    }

#%% chargement des donnees
# lecture brute et ajout des colonnes géospatiales pour trier c1 et c2
df = pd.read_csv(PATH_CSV, sep=';', encoding='utf-8')
df[['X', 'Y']] = df['WKT'].apply(lambda x: pd.Series(extract_centroid(x)))
df['Cellule'] = np.where(df['X'] < LIMITE_X, 'C1 ', 'C2 (Témoin)')

#%% fonctions graphiques pour les cartes

def tracer_planche_cartes(config_list):
    # boucle pour générer les cartes de variations de hauteurs
    n = len(config_list)
    fig, axs = plt.subplots(n, 1, figsize=(16, 5.5 * n), facecolor='white')
    if n == 1: axs = [axs]
    norm_map = TwoSlopeNorm(vmin=-1.5, vcenter=0, vmax=1.5)
    cmap = plt.cm.RdBu
    
    for i, p in enumerate(config_list):
        ax = axs[i]
        ax.set_facecolor('#C0C0C0') 
        col = p["col_name"]
        if col in df.columns:
            df_p = df.dropna(subset=[col])
            
            # calcul des limites au plus près des mailles du relevé
            p_xmin, p_xmax = df_p['X'].min() - 5, df_p['X'].max() + 5
            p_ymin, p_ymax = df_p['Y'].min() - 5, df_p['Y'].max() + 5
            
            # coloration rouge (érosion) / bleu (accrétion) maille par maille
            for _, row in df_p.iterrows():
                val = row[col]
                c = '#FFFFFF' if abs(val) < SEUIL_DETECTION else cmap(norm_map(val))
                ax.add_patch(Rectangle((row["X"]-5, row["Y"]-5), 10, 10, facecolor=c, linewidth=0, zorder=2))
            
            # cadrage propre de la figure
            ax.set_aspect('equal')
            ax.set_xlim(p_xmin, p_xmax)
            ax.set_ylim(p_ymin, p_ymax)
            
            # tracé de la limite et placement des étiquettes des cellules
            ax.axvline(LIMITE_X, color='red', ls='--', alpha=0.7, zorder=3, label='Séparation entre les cellules')
            ax.text(p_xmin + (LIMITE_X - p_xmin)/2, p_ymax - (p_ymax - p_ymin)*0.3, "CELLULE 1", fontweight='bold', ha='center', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
            ax.text(LIMITE_X + (p_xmax - LIMITE_X)/2, p_ymax - (p_ymax - p_ymin)*0.3, "CELLULE 2 (Témoin)", fontweight='bold', ha='center', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
            
            ax.set_title(f"Différentiel altimétrique : {p['label']} \n(Blanc = Stable < 5cm - gris = masque)", fontweight='bold', fontsize=18, pad=10)
            ax.legend(loc='upper right', fontsize=8)
            
            # paramétrage des légendes de la barre de couleur
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm_map)
            cbar = fig.colorbar(sm, ax=ax, orientation='vertical', fraction=0.015, pad=0.02)
            cbar.set_label("Variation d'élévation (m)", fontweight='bold', fontsize=10)
            cbar.ax.text(4, 1.0, 'ACCRÉTION', va='center', fontweight='bold', color='#053061', fontsize=9)
            cbar.ax.text(5, 0.0, 'STABLE', va='center', fontweight='bold', color='black', fontsize=9)
            cbar.ax.text(4, -1.0, 'ÉROSION', va='center', fontweight='bold', color='#67001f', fontsize=9)

#%% fonctions graphiques pour les gaussiennes

def tracer_planche_gaussiennes(config_list, titre_groupe):
    # boucle pour tracer l'ajustement statistique normal des deux cellules
    n = len(config_list)
    fig, axs = plt.subplots(n, 1, figsize=(10, 4 * n), facecolor='white')
    if n == 1: axs = [axs]
    for i, p in enumerate(config_list):
        ax = axs[i]; col = p["col_name"]
        if col in df.columns:
            for cell, color, lcolor in zip(['C1 ', 'C2 (Témoin)'], ['blue', 'orange'], ['darkblue', 'darkorange']):
                d = df[df['Cellule'] == cell][col].dropna()
                if not d.empty:
                    # histogramme de fond et courbe de la loi normale par dessus
                    ax.hist(d, bins=60, color=color, alpha=0.2, density=True, label=f"Distribution {cell}")
                    mu, std = norm.fit(d); x_axis = np.linspace(d.min(), d.max(), 100)
                    ax.plot(x_axis, norm.pdf(x_axis, mu, std), color=lcolor, lw=2, linestyle='--', label=f"Gaussienne {cell}")
            # ajout graphique des lignes d'incertitude à 5cm
            ax.axvline(0, color='black', lw=2, zorder=5)
            ax.axvline(SEUIL_DETECTION, color='red', ls='--', lw=1.2, label='Incertitude ±5cm')
            ax.axvline(-SEUIL_DETECTION, color='red', ls='--', lw=1.2)
            ax.axvspan(-SEUIL_DETECTION, SEUIL_DETECTION, color='red', alpha=0.05)
            ax.set_title(f"Analyses statistiques (zone Sud): {p['label']}", fontweight='bold', fontsize=12)
            ax.legend(fontsize=8, loc='upper right')
    fig.suptitle(titre_groupe, fontweight='bold', fontsize=14, y=1.01); plt.tight_layout(pad=2.0)

#%% generation des graphiques et des planches
# lancements des fonctions d'affichages des cartes et graphiques
tracer_planche_cartes(config_saisons)
tracer_planche_cartes(config_annuel)
tracer_planche_gaussiennes(config_saisons, "DISTRIBUTIONS STATISTIQUES - SAISONNIER")
tracer_planche_gaussiennes(config_annuel, "DISTRIBUTIONS STATISTIQUES - ANNUEL")

#%% generation et traitement des tableaux comptables
#tableaux des bilans sédimentaires

fig_bilan = plt.figure(figsize=(19, 5.2 * int(np.ceil(len(periodes_totales)/2))), facecolor='white')
gs_b = plt.GridSpec(int(np.ceil(len(periodes_totales)/2)), 2, wspace=0.22, hspace=0.5)

for i, p in enumerate(periodes_totales):
    col = p["col_name"]
    if col in df.columns:
        s1 = calculer_stats(df[df['Cellule'] == 'C1 '], col)
        s2 = calculer_stats(df[df['Cellule'] == 'C2 (Témoin)'], col)
        st = calculer_stats(df, col)
        
        row_grid = i // 2
        col_grid = i % 2
        ax_b = fig_bilan.add_subplot(gs_b[row_grid, col_grid])
        ax_b.axis('off')
        
        bilan_data = [
            ['C1', s1['bilan'][0], s1['bilan'][1], s1['bilan'][2], s1['bilan'][3], s1['bilan'][4]], 
            ['C2', s2['bilan'][0], s2['bilan'][1], s2['bilan'][2], s2['bilan'][3], s2['bilan'][4]], 
            ['TOTAL', st['bilan'][0], st['bilan'][1], st['bilan'][2], st['bilan'][3], st['bilan'][4]]
        ]
        
        c1_dz_color = '#b3cde3' if s1["val_net"] >= 0 else '#fbb4ae'
        c2_dz_color = '#b3cde3' if s2["val_net"] >= 0 else '#fbb4ae'
        ct_dz_color = '#b3cde3' if st["val_net"] >= 0 else '#fbb4ae'
        
        bilan_colors = [
            ['#1f77b4', 'white', 'white', 'white', 'white', c1_dz_color],
            ['#ff7f0e', 'white', 'white', 'white', 'white', c2_dz_color],
            ['#d3d3d3', '#d3d3d3', '#d3d3d3', '#d3d3d3', '#d3d3d3', ct_dz_color]
        ]
        
        t1 = ax_b.table(cellText=bilan_data, 
                        colLabels=['Cellule', 'Surface (m²)', 'Gains (m³)', 'Pertes (m³)', 'Bilan net (m³)', 'ΔZ (cm)'], 
                        loc='center', cellLoc='center', cellColours=bilan_colors)
        t1.scale(1.05, 2.4) 
        t1.auto_set_font_size(False)
        t1.set_fontsize(9.5) # Taille de base pour les en-têtes
        
        for (row_idx, col_idx), cell_obj in t1.get_celld().items():
            if row_idx == 0:
                cell_obj.set_facecolor('#444444')
                cell_obj.get_text().set_color('white')
                cell_obj.get_text().set_weight('bold')
            elif row_idx > 0 and col_idx == 0:
                if row_idx <= 2: cell_obj.get_text().set_color('white')
                cell_obj.get_text().set_weight('bold')
            elif row_idx > 0: 
                # C'EST ICI : Augmente la taille des nombres dans les cases de données
                cell_obj.get_text().set_fontsize(13)
                
                if row_idx == 3: # Ligne TOTAL
                    cell_obj.get_text().set_weight('normal')
                    if col_idx < 5:
                        cell_obj.set_facecolor('#d3d3d3')
            
            if col_idx == 5: 
                cell_obj.get_text().set_weight('bold')
                
        ax_b.set_title(f"Bilan sédimentaire : {p['label']}", fontweight='bold', fontsize=11.5, pad=10)

#tableaux de fiabilité du modèle

fig_fiab = plt.figure(figsize=(16, 5.0 * int(np.ceil(len(periodes_totales)/2))), facecolor='white')
gs_f = plt.GridSpec(int(np.ceil(len(periodes_totales)/2)), 2, wspace=0.22, hspace=0.5)

for i, p in enumerate(periodes_totales):
    col = p["col_name"]
    if col in df.columns:
        s1 = calculer_stats(df[df['Cellule'] == 'C1 '], col)
        s2 = calculer_stats(df[df['Cellule'] == 'C2 (Témoin)'], col)
        st = calculer_stats(df, col)
        
        row_grid = i // 2
        col_grid = i % 2
        ax_f = fig_fiab.add_subplot(gs_f[row_grid, col_grid])
        ax_f.axis('off')
        
        fiab_data = [
            ['C1', s1['fiab'][0], s1['fiab'][1], s1['fiab'][2]], 
            ['C2', s2['fiab'][0], s2['fiab'][1], s2['fiab'][2]], 
            ['TOTAL', st['fiab'][0], st['fiab'][1], st['fiab'][2]]
        ]
        
        fiab_colors = [
            ['#1f77b4', 'white', 'white', 'white'], 
            ['#ff7f0e', 'white', 'white', 'white'], 
            ['#d3d3d3', '#d3d3d3', '#d3d3d3', '#d3d3d3']
        ]
        
        t2 = ax_f.table(cellText=fiab_data, 
                        colLabels=['Cellule', 'Incert. (m³)', 'Brassé (m³)', 'Fiabilité'], 
                        loc='center', cellLoc='center', cellColours=fiab_colors)
        t2.scale(1.05, 2.4)
        t2.auto_set_font_size(False)
        t2.set_fontsize(9.5) # Taille de base pour les en-têtes
        
        for (row_idx, col_idx), cell_obj in t2.get_celld().items():
            if row_idx == 0:
                cell_obj.set_facecolor('#444444')
                cell_obj.get_text().set_color('white')
                cell_obj.get_text().set_weight('bold')
            elif row_idx > 0 and col_idx == 0:
                if row_idx <= 2: cell_obj.get_text().set_color('white')
                cell_obj.get_text().set_weight('bold')
            elif row_idx > 0: 
                # C'EST ICI : Augmente la taille des nombres de fiabilité
                cell_obj.get_text().set_fontsize(11)
                
                if row_idx == 3: 
                    cell_obj.get_text().set_weight('normal')
            
            if col_idx == 3: 
                cell_obj.get_text().set_weight('bold')
                
        ax_f.set_title(f"Fiabilité du modèle : {p['label']}", fontweight='bold', fontsize=11.5, pad=10)

plt.show()
