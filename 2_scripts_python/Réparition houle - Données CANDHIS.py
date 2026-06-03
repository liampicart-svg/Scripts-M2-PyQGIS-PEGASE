# -*- coding: utf-8 -*-
"""
Created on Tue Jun  2 11:34:47 2026

@author: l.picart
"""
# -*- coding: utf-8 -*-
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import os
from matplotlib.gridspec import GridSpec

#%% configuration
# chemin vers le répertoire contenant les fichiers csv archives de CANDHIS
dossier_brut = r"C:\Liam\Python\Données candhis\Données brutes"

# selection des annees d'analyse
#annees_voulues = [2024, 2025]  
annees_voulues = [2014, 2015] 

all_dfs = []

#%% chargement et uniformisation des fichiers csv
for annee in annees_voulues:
    nom_f = f"Candhis_03404_{annee}_arch.csv"
    chemin = os.path.join(dossier_brut, nom_f)
    if os.path.exists(chemin):
        try:
            # lecture brute avec gestion du separateur europeen
            df_temp = pd.read_csv(chemin, sep=";", decimal=".", encoding="utf-8")
            
            # verification et correction automatique de l inversion jour/mois des dates
            dates = pd.to_datetime(df_temp["DateHeure"], errors='coerce')
            if dates.isna().sum() > len(df_temp)*0.1 or (not dates.empty and dates.dt.day.max() <= 12):
                dates = pd.to_datetime(df_temp["DateHeure"], dayfirst=True, errors='coerce')
            df_temp["DateHeure"] = dates
            
            # conversion explicite des chaines en flottants numeriques
            for col in ["HM0", "THETAP"]:
                df_temp[col] = pd.to_numeric(df_temp[col].astype(str).str.replace(',', '.'), errors='coerce')
            all_dfs.append(df_temp)
            print(f"✅ {nom_f} chargé")
        except Exception as e:
            print(f"❌ Erreur sur {nom_f} : {e}")

if not all_dfs:
    print("❌ Aucune donnée trouvée !")
    exit()

# concatenation et filtrage des valeurs aberrantes ou des mesures hors limites
df_global = pd.concat(all_dfs, ignore_index=True).dropna(subset=["DateHeure", "HM0", "THETAP"])
df_global = df_global[(df_global["HM0"] < 5) & (df_global["THETAP"] <= 360)]

#%% initialisation de la planche graphique avec gridspec
fig = plt.figure(figsize=(18, 12), facecolor='white')
# creation d une grille asymetrique pour agencer les figures temporelles et directionnelles
gs = GridSpec(2, 2, figure=fig, height_ratios=[1, 1], hspace=0.4, wspace=0.3)

#%% trace du nuage de points de la serie chronologique (ax1)
# prend toute la largeur de la premiere ligne pour mettre en evidence les tempetes
ax1 = fig.add_subplot(gs[0, :]) 
scatter = ax1.scatter(df_global["DateHeure"], df_global["HM0"], 
                      c=df_global["THETAP"], cmap='hsv', 
                      s=8, alpha=0.6, vmin=0, vmax=360)

# configuration de la colorbar associee aux secteurs directionnels
cbar = fig.colorbar(scatter, ax=ax1, pad=0.01)
cbar.set_label("Direction de pic $\\theta_p$ (°N)", fontweight='bold')
cbar.set_ticks([0, 90, 180, 270, 360])
cbar.set_ticklabels(['N', 'E', 'S', 'W', 'N'])

# mise en forme de l axe temporel mois par mois
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')

ax1.set_title("Chronologie des états de mer (Hauteur et Direction) de 2024 à 2025", fontsize=14, fontweight='bold')
ax1.set_ylabel("Hauteur $H_{m0}$ (m)", fontweight='bold')
ax1.grid(True, linestyle='--', alpha=0.5)

#%% generation de la rose des fréquences directionnelles (ax_rose)
# utilise une projection polaire pour illustrer la provenance des houles (sud-est dominant)
ax_rose = fig.add_subplot(gs[1, 0], projection='polar')
nb_secteurs = 16
bins_dir = np.linspace(0, 360, nb_secteurs + 1)
bins_h = [0, 1, 2, 3, 5]
# echelle de couleurs calquee sur les classes d intensite energetique
couleurs_h = ['#31a354', '#addd8e', '#feb24c', '#e31a1c']

# calcul de l histogramme bidimensionnel (direction vs hauteur)
hist2d, _, _ = np.histogram2d(df_global["THETAP"], df_global["HM0"], bins=[bins_dir, bins_h])
hist_pc = (hist2d / len(df_global)) * 100
angles = np.deg2rad(bins_dir[:-1] + (360/nb_secteurs)/2)
largeur = np.deg2rad(360/nb_secteurs)

# empilement des barres par classe de hauteur de vagues
bottom = np.zeros(nb_secteurs)
for i in range(len(bins_h)-1):
    ax_rose.bar(angles, hist_pc[:, i], width=largeur, bottom=bottom, 
                color=couleurs_h[i], edgecolor='black', alpha=0.8, 
                label=f"{bins_h[i]}-{bins_h[i+1]}m")
    bottom += hist_pc[:, i]

# calage de la rose sur le nord geographique avec rotation horaire
ax_rose.set_theta_zero_location('N')
ax_rose.set_theta_direction(-1)
ax_rose.set_xticks(np.linspace(0, 2*np.pi, 4, endpoint=False))
ax_rose.set_xticklabels(['N', 'E', 'S', 'W'], fontweight='bold')
ax_rose.set_title("Distribution directionnelle (%)", pad=30, fontweight='bold')
ax_rose.legend(title="$H_{m0}$ (m)", loc='lower right', bbox_to_anchor=(1.3, 0))

#%% trace de l histogramme des frequences des hauteurs (ax_hist)
# permet de verifier la repartition statistique et l occurrence des etats de mer calmes
ax_hist = fig.add_subplot(gs[1, 1])
n, bins, patches = ax_hist.hist(df_global["HM0"], bins=40, edgecolor='black', alpha=0.7)

# lissage colorimetrique des barres pour correspondre a la legende de la rose
for i in range(len(patches)):
    if bins[i] < 1: patches[i].set_facecolor('#31a354')
    elif bins[i] < 2: patches[i].set_facecolor('#addd8e')
    elif bins[i] < 3: patches[i].set_facecolor('#feb24c')
    else: patches[i].set_facecolor('#e31a1c')

ax_hist.set_title("Fréquence d'apparition des hauteurs", fontsize=12, fontweight='bold')
ax_hist.set_xlabel("Hauteur $H_{m0}$ (m)")
ax_hist.set_ylabel("Nombre de relevés")
ax_hist.grid(axis='y', alpha=0.3)

#%% ajustements finaux et affichage
plt.subplots_adjust(top=0.92, bottom=0.10, left=0.08, right=0.95)
plt.show()

print(f"Analyse terminée. Points affichés : {len(df_global)}")
