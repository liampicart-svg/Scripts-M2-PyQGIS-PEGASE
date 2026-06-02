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

PATH_CSV = r"C:\Liam\QGIS\PEGASE_Projet_Liam\Comparaison\Saison\Excel_maillage_cube\VARIATIONS_ELEVATION_MAILLAGE-MATRICE_COMPLETE_Zone_Sud_c0.csv"

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
        "bilan": [f"{surf:,.1f}", f"+{gains:,.1f}", f"{pertes:,.1f}", f"{net:+.1f}", f"{dz:+.2f}"],
        "fiab": [f"{v_incert:,.1f}", f"{v_brasse:,.1f}", f"{fiab:.2f} %"],
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

#%% generation et traitement des tableaux comtabiles
# création de la planche pour les rendus des tableaux comptables
fig_t = plt.figure(figsize=(16, 3 * len(periodes_totales)), facecolor='white')
gs = plt.GridSpec(len(periodes_totales), 2, wspace=0.1, hspace=0.4)

for i, p in enumerate(periodes_totales):
    col = p["col_name"]
    if col in df.columns:
        # extraction des calculs pour chaque sous-tableau
        s1 = calculer_stats(df[df['Cellule'] == 'C1 '], col)
        s2 = calculer_stats(df[df['Cellule'] == 'C2 (Témoin)'], col)
        st = calculer_stats(df, col)
        
        def get_row_colors(stat_dict, base_color):
            # coloration automatique : bleu pour positif, rouge pour négatif
            row_colors = [base_color, 'white', 'white', 'white']
            c = '#85b6e4' if stat_dict["val_net"] >= 0 else '#f4cccc'
            row_colors.extend([c, c]) 
            return row_colors

        # premier tableau : les volumes et les bilans sédimentaires nets
        ax_b = fig_t.add_subplot(gs[i, 0]); ax_b.axis('off')
        bilan_data = [['C1']+s1["bilan"], ['C2']+s2["bilan"], ['TOTAL']+st["bilan"]]
        bilan_colors = [get_row_colors(s1, '#1f77b4'), get_row_colors(s2, '#ff7f0e'), get_row_colors(st, '#d3d3d3')]
        
        t1 = ax_b.table(cellText=bilan_data, 
                        colLabels=['Cellule','Surface','Gains','Pertes','Bilan net','ΔZ (cm)'], 
                        loc='center', cellLoc='center', cellColours=bilan_colors)
        t1.scale(1, 2.2); ax_b.set_title(f"Bilan sédimentaire : {p['label']}", fontweight='bold', fontsize=12)
        
        # deuxième tableau : les indices de fiabilité associés
        ax_f = fig_t.add_subplot(gs[i, 1]); ax_f.axis('off')
        t2 = ax_f.table(cellText=[['C1']+s1["fiab"], ['C2']+s2["fiab"], ['TOTAL']+st["fiab"]], 
                        colLabels=['Cellule','Incert.','Brassé','Fiabilité'], loc='center', cellLoc='center',
                        cellColours=[['#1f77b4']+['white']*3, ['#ff7f0e']+['white']*3, ['#d3d3d3']*4])
        t2.scale(1, 2.2); ax_f.set_title(f"Fiabilité du modèle : {p['label']}", fontweight='bold', fontsize=12)

plt.show()