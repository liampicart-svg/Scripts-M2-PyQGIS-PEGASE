# 1. outils d'extraction sous pyqgis

ce dossier contient les scripts à lancer dans la console python de qgis. 

## à quoi ça sert ?
ils automatisent les tâches répétitives sur qgis :
1. ils chargent le maillage d'analyse et vérifient les géométries.
2. ils calculent les mnt différentiels (le mnt récent moins le mnt ancien) avec la calculatrice raster.
3. ils croisent ces cartes avec les mailles (statistiques de zone) pour calculer la variation altimétrique moyenne de chaque carré.
4. ils exportent le tout dans un fichier csv propre et nettoyé.

**rôle dans la chaîne** : c'est l'étape de production. ces scripts génèrent les fichiers de données brutes qui alimenteront ensuite toute la partie statistique dans le fichier 2.
