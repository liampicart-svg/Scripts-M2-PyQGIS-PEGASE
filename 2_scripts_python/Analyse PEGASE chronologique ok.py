# -*- coding: utf-8 -*-
"""
Created on Tue Jun  2 13:57:15 2026

@author: l.picart
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
import os
from datetime import datetime
from matplotlib.lines import Line2D

#%% configuration
# chemin absolu vers le fichier de donnees issues de qgis
PATH_CSV = r"C:\Liam\QGIS\PEGASE_Projet_Liam\Comparaison\Analyse PEGASE\Excel_maillage_cube\VARIATIONS_ELEVATION_MAILLAGE-CHRONO_PEGASE3_c0.csv"

LIMITE_X = 736480 # limite geographique en x (lambert 93) pour separer la cellule 1 de la cellule 2
SURFACE_MAILLE = 99.878 # surface d une maille elementaire en m2 (ici cube de 10m x 10m)
ORDRE_ZONES = [1, 2, 3, 4, 5] # liste des numeros des zones geographiques a analyser sur le site
SEUIL_MIN_MAILLES = 10 # nombre minimal de mailles detectees requis pour valider un calcul statistique
INCERTITUDE_CM = 5  # seuil d incertitude fixe en cm lie au bruit de mesure des appareils (rtk/lidar)
COULEURS_ZONES = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'] #couleurs pour les zones

# dates cles des amenagements pour tracer les lignes verticales de repere
DATE_BRISE_LAMES = datetime(2013, 6, 1)
DATE_INSTALL_PEGASE = datetime(2022, 6, 1)

#%% formatage des dates et géométries
def clean_date(s):
    # tente de lire les differents formats de dates dans les entetes de colonne
    s = str(s).strip()
    m = re.search(r'(\d{2})_(\d{2})_(\d{4})', s)
    if m: return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.search(r'(\d{4})_(\d{2})_(\d{2})', s)
    if m: return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})', s)
    if m: return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.search(r'(\d{4})/(\d{2})/(\d{2})', s)
    if m: return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m: return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'(\d{4})', s)
    if m: return datetime(int(m.group(1)), 1, 1)
    return None

def get_x(wkt):
    # recupere le premier nombre x de la chaine geometrique wkt
    try: return float(re.findall(r"[-+]?\d*\.?\d+", str(wkt))[0])
    except: return 0.0

#%% chargement et tri des colonnes temporelles
if not os.path.exists(PATH_CSV):
    print(f"Erreur : Fichier introuvable à {PATH_CSV}")
else:
    df = pd.read_csv(PATH_CSV, sep=';', encoding='utf-8-sig')
    col_wkt = 'wkt_geom' if 'wkt_geom' in df.columns else 'WKT'
    df['X'] = df[col_wkt].apply(get_x)
    df['Cellule'] = np.where(df['X'] < LIMITE_X, 'Cellule 1 (PEGASE)', 'Cellule 2 (témoin)')
    df['Num'] = pd.to_numeric(df['Num'], errors='coerce')

    # isolement des colonnes de variations sédimentaires simples (sans écart-type)
    cols_vs = [c for c in df.columns if ' vs ' in c and not c.endswith('_std')]
    chrono_data = [] 
    for c in cols_vs:
        parts = c.split(' vs ')
        d_deb, d_fin = clean_date(parts[0]), clean_date(parts[1])
        if d_deb and d_fin:
            col_std = f"{c}_std" if f"{c}_std" in df.columns else None
            chrono_data.append((d_deb, d_fin, c, col_std))

    # tri de la chronologie par date de fin du releve
    chrono_data.sort(key=lambda x: x[1])
    all_dates_dt = sorted(list(set([x[0] for x in chrono_data] + [x[1] for x in chrono_data])))
    sorted_dates_str = [d.strftime('%d/%m/%Y') for d in all_dates_dt]

    if not chrono_data:
        print("Erreur : Aucune donnée exploitable.")
    else:
#%% calcul cumulatif des volumes et de l elevation
        cellules = ['Cellule 1 (PEGASE)', 'Cellule 2 (témoin)']
        results = {c: {z: {'dz': [0.0]*len(all_dates_dt), 'vol': [0.0]*len(all_dates_dt), 
                           'std_dz': [0.0]*len(all_dates_dt), 'std_vol': [0.0]*len(all_dates_dt),
                           'n': [0]*len(all_dates_dt)} 
                       for z in ORDRE_ZONES} for c in cellules}
        n_max_dict = {c: {z: len(df[(df['Cellule']==c) & (df['Num']==z)]) for z in ORDRE_ZONES} for c in cellules}

        for cell in cellules:
            for z in ORDRE_ZONES:
                current_dz, current_vol = 0.0, 0.0
                n_max = n_max_dict[cell][z]
                results[cell][z]['n'][0] = n_max

                for d_deb, d_fin, col_name, col_std in chrono_data:
                    idx_fin = all_dates_dt.index(d_fin)
                    sub_moy = pd.to_numeric(df[(df['Cellule']==cell) & (df['Num']==z)][col_name], errors='coerce').dropna()
                    n = len(sub_moy)
                    results[cell][z]['n'][idx_fin] = n
                    
                    # integration des valeurs moyennes ponderees si le nombre de mailles suffit
                    if n >= SEUIL_MIN_MAILLES:
                        moy = sub_moy.mean()
                        current_dz += (moy * 100)
                        current_vol += (moy * n_max * SURFACE_MAILLE)
                        
                        if col_std:
                            sub_std = pd.to_numeric(df[(df['Cellule']==cell) & (df['Num']==z)][col_std], errors='coerce').dropna()
                            val_std_reelle_m = sub_std.mean()
                        else:
                            val_std_reelle_m = 0.0
                            
                        results[cell][z]['dz'][idx_fin] = current_dz
                        results[cell][z]['vol'][idx_fin] = current_vol
                        results[cell][z]['std_dz'][idx_fin] = val_std_reelle_m * 100
                        results[cell][z]['std_vol'][idx_fin] = val_std_reelle_m * n_max * SURFACE_MAILLE

        # preparation des masques pour separer l avant/apres pegase
        jours_ecoules = np.array([(d - all_dates_dt[0]).days for d in all_dates_dt])
        seuil_jours_pegase = (DATE_INSTALL_PEGASE - all_dates_dt[0]).days

        idx_avant = jours_ecoules <= seuil_jours_pegase
        idx_apres = jours_ecoules >= seuil_jours_pegase
        idx_total = np.ones(len(all_dates_dt), dtype=bool)

#%% tracage des courbes chronologiques
        idx_full = np.arange(len(all_dates_dt))
        for cell in cellules:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), facecolor='white')
            fig.suptitle(f"Analyse chronologique des stocks sédimentaires - {cell}", fontsize=14, fontweight='bold')

            for i, z in enumerate(ORDRE_ZONES):
                n_max = n_max_dict[cell][z]
                dz_brut = np.array(results[cell][z]['dz'])
                vol_brut = np.array(results[cell][z]['vol'])
                n_relevements = np.array(results[cell][z]['n'])
                
                std_dz_p = np.array(results[cell][z]['std_dz'])
                std_vol_p = np.array(results[cell][z]['std_vol'])
                
                # masquage des donnees si la couverture de la zone descend sous les 50%
                dz_p = []
                vol_p = []
                for k, (v_dz, v_vol) in enumerate(zip(dz_brut, vol_brut)):
                    if k == 0:
                        dz_p.append(0.0)
                        vol_p.append(0.0)
                    elif n_relevements[k] < (n_max / 2) or v_dz == 0:
                        dz_p.append(np.nan)
                        vol_p.append(np.nan)
                    else:
                        dz_p.append(v_dz)
                        vol_p.append(v_vol)
                
                dz_p = np.array(dz_p)
                vol_p = np.array(vol_p)

                # ajout graphique de l enveloppe de dispersion spatiale a 1 sigma
                ax1.fill_between(idx_full, dz_p - std_dz_p, dz_p + std_dz_p, color=COULEURS_ZONES[i], alpha=0.10, zorder=2)
                ax2.fill_between(idx_full, vol_p - std_vol_p, vol_p + std_vol_p, color=COULEURS_ZONES[i], alpha=0.10, zorder=2)

                # trace continu des trajectoires des zones
                ax1.plot(idx_full, dz_p, color=COULEURS_ZONES[i], lw=2.5, label=f"Zone {z}", zorder=4)
                ax2.plot(idx_full, vol_p, color=COULEURS_ZONES[i], lw=2.5, label=f"Zone {z}", zorder=4)

                # ajout des marqueurs (croix coloree selon la zone si la couverture descend sous les 50%)
                for k, idx in enumerate(idx_full):
                    n_actuel = n_relevements[k]
                    if k == 0 or dz_brut[k] != 0:
                        if n_actuel < n_max / 2:
                            ax1.plot(idx, dz_brut[k], marker='x', color=COULEURS_ZONES[i], markersize=8, markeredgewidth=2.5, alpha=0.8, zorder=6)
                            ax2.plot(idx, vol_brut[k], marker='x', color=COULEURS_ZONES[i], markersize=8, markeredgewidth=2.5, alpha=0.8, zorder=6)
                        else:
                            ax1.plot(idx, dz_p[k], marker='o', color=COULEURS_ZONES[i], markersize=5, zorder=6)
                            ax2.plot(idx, vol_p[k], marker='s', color=COULEURS_ZONES[i], markersize=5, zorder=6)

            # parametrage des axes et labels des subplots
            for ax, lab, unit in zip([ax1, ax2], ["Variation d'élévation", "Bilan volumétrique"], ["cm", "m³"]):
                ax.set_ylabel(f"{lab} ({unit})", fontweight='bold')
                ax.grid(True, alpha=0.2, zorder=1)
                ax.axhline(0, color='black', alpha=0.5, zorder=3)

                ax.set_xticks(idx_full)
                ax.set_xticklabels([("\n"*(k%3))+d for k, d in enumerate(sorted_dates_str)], fontsize=8)
                
                # placement des lignes verticales pour les dates clefs des amenagements
                dates_ts = [d.timestamp() for d in all_dates_dt]
                for d_ev, txt, col_ev in zip([DATE_BRISE_LAMES, DATE_INSTALL_PEGASE], ["Brise-lames", "PEGASE"], ["red", "green"]):
                    if cell == 'Cellule 2 (témoin)' and txt == "PEGASE": continue
                    if all_dates_dt[0].timestamp() <= d_ev.timestamp() <= all_dates_dt[-1].timestamp():
                        x_ev = np.interp(d_ev.timestamp(), dates_ts, idx_full)
                        ax.axvline(x_ev, color=col_ev, ls='--', alpha=0.5, lw=1.5, zorder=3)
                        ax.text(x_ev, ax.get_ylim()[1]*0.87, f" {txt}", color=col_ev, fontweight='bold', zorder=6)
                
                handles, labels = ax.get_legend_handles_labels()
                sign_handle = Line2D([0], [0], marker='x', color='black', linestyle='None', markersize=8, markeredgewidth=2, label='Données < 50% (couleur de zone)')
                std_handle = Line2D([0], [0], color='black', lw=6, alpha=0.2, label='Dispersion spatiale ($\pm1\sigma$ pixels)')
                
                handles.extend([sign_handle, std_handle])
                ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1, 1))

            plt.tight_layout(rect=[0, 0, 0.82, 1])

#%% generation des boites a moustaches au dernier etat disponible
        for cell in cellules:
            fig_box, ax_box = plt.subplots(figsize=(12, 6), facecolor='white')
            
            boxplot_data = []
            for z in ORDRE_ZONES:
                last_col = chrono_data[-1][2]
                sub_data = pd.to_numeric(df[(df['Cellule']==cell) & (df['Num']==z)][last_col], errors='coerce').dropna()
                boxplot_data.append(sub_data * 100)
            
            bp = ax_box.boxplot(boxplot_data, patch_artist=True, labels=[f"Zone {z}" for z in ORDRE_ZONES], showmeans=True)
            
            for patch, color in zip(bp['boxes'], COULEURS_ZONES):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)
            for whisker in bp['whiskers']: whisker.set(color='black', linewidth=1.2, linestyle='--')
            for cap in bp['caps']: cap.set(color='black', linewidth=1.2)
            for median in bp['medians']: median.set(color='red', linewidth=2)
            for mean in bp['means']: mean.set(marker='D', markerfacecolor='white', markeredgecolor='black', markersize=6)

            ax_box.axhspan(-INCERTITUDE_CM, INCERTITUDE_CM, color='gray', alpha=0.15, label='Bruit instrumental (±5 cm)')
            ax_box.axhline(0, color='black', lw=1, alpha=0.5)

            ax_box.set_ylabel("Variation d'élévation dZ (cm)", fontweight='bold')
            ax_box.set_title(f"Distribution spatiale et dispersion des dZ au dernier relevé - {cell}", fontsize=12, fontweight='bold', pad=15)
            ax_box.grid(True, alpha=0.2)
            ax_box.legend(loc='upper right')

#%% generation des tableaux de controle du nombre de mailles detectees
        for cell in cellules:
            fig_tab, ax_tab = plt.subplots(figsize=(12, 5), facecolor='white')
            ax_tab.axis('off')
            header = [f"Zone {z}" for z in ORDRE_ZONES]
            row_labels = ["MAX de la maille"] + sorted_dates_str[1:]
            cell_text = []
            cell_colors = [['#f2f2f2'] * len(ORDRE_ZONES)]
            cell_text.append([n_max_dict[cell][z] for z in ORDRE_ZONES])
            
            for i in range(1, len(all_dates_dt)):
                row_vals, row_cols = [], []
                for z in ORDRE_ZONES:
                    n = results[cell][z]['n'][i]
                    n_max = n_max_dict[cell][z]
                    row_vals.append(n)
                    if n == 0: row_cols.append('#ff9999')
                    elif (n / n_max) < 0.5: row_cols.append('#ffcc99')
                    else: row_cols.append('white')
                cell_text.append(row_vals)
                cell_colors.append(row_cols)

            table = ax_tab.table(cellText=cell_text, rowLabels=row_labels, colLabels=header,
                                 colColours=COULEURS_ZONES, cellColours=cell_colors, loc='center')
            for (row, col), cell_obj in table.get_celld().items():
                if row == 0:
                    cell_obj.get_text().set_color('white')
                    cell_obj.get_text().set_weight('bold')
            table.scale(1, 1.8); table.auto_set_font_size(False); table.set_fontsize(10)
            plt.title(f"Disponibilité du nombre de mailles par relevé et par zone - {cell}", fontweight='bold', pad=20)
            
        plt.show()
