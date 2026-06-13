# 1. Outils d'extraction sous pyqgis

Ce dossier contient les scripts à lancer dans la console python de qgis. 

## A quoi ça sert ?
Ils automatisent les tâches répétitives sur qgis :
1. Ils chargent le maillage d'analyse et vérifient les géométries.
2. Ils calculent les mnt différentiels (le mnt récent moins le mnt ancien) avec la calculatrice raster.
3. Ils croisent ces cartes avec les mailles (statistiques de zone) pour calculer la variation altimétrique moyenne de chaque carré.
4. Ils exportent le tout dans un fichier csv propre et nettoyé.

**Rôle dans la chaîne** : c'est l'étape de production. Ces scripts génèrent les fichiers de données brutes qui alimenteront ensuite toute la partie statistique dans le fichier 2.
