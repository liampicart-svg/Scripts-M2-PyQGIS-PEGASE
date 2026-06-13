# 2. Scripts d'analyse statistique et graphiques python

Ce dossier contient les scripts python destinés à l'interprétation sédimentaire et à la création des figures du rapport.

## A quoi ça sert ?
Ils gèrent toute la partie scientifique et visuelle :
* Ils calcul des bilans de volumes nets (gains et pertes) en appliquant le seuil d'incertitude des 5 cm.
* Ils tracé des courbes chronologiques d'évolution des stocks de sable et calcul des droites de tendance.
* Ils création des planches de gaussiennes et des boxplots pour observer la dispersion.
* Ils analyse et croisement des états de mer (hauteur et direction) issus des données candhis.

**Attention** :   Ces scripts ne peuvent pas fonctionner seuls. Ils se basent entièrement sur les fichiers csv extraits et structurés par les scripts du dossier **1_scripts_pyqgis**.
