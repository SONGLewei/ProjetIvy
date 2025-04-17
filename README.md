1. Création des étages  
Après avoir lancé `main.py`, l'utilisateur doit cliquer en haut à gauche pour créer un nouvel étage.  
Le premier étage est automatiquement nommé "Floor 0".  
Un clic droit sur un étage permet de renommer l'étage ou de définir sa hauteur.

2. Ajout de nouveaux étages  
Chaque nouvel étage est ajouté au-dessus de l'étage sélectionné.  
Actuellement, la suppression des étages n’est pas possible (fonctionnalité non prévue).

3. Outils de dessin  
Sur chaque étage, l'utilisateur peut dessiner :
- Des murs (noir, par défaut)
- Des fenêtres (violet clair)
- Des portes (marron)
- Quatre types de gaines de ventilation (avec couleurs différentes)

Après avoir cliqué sur l’outil “ventilation”, un menu permet de choisir le type de gaine (couleur + fonction).  
L’utilisateur doit ensuite renseigner le nom, le diamètre et le débit d’air pour chaque gaine (les dialogues s’affichent automatiquement).

4. Affichage des informations  
Après la création d’une gaine, un survol avec la souris de plus d’1 seconde affiche les informations suivantes :  
- Nom  
- Diamètre  
- Débit  
- Fonction

5. Gomme  
Après avoir sélectionné l’outil gomme, un simple clic sur un élément du dessin le supprime.

6. Sécurité d’interaction  
Un simple clic sur le canvas sans avoir sélectionné d’outil ne déclenche aucune action.

7. Aide visuelle  
En haut à gauche, une boussole et une règle indiquent les directions (N/E/S/O) et une échelle de 2 mètres.

8. Contrôle du canvas  
Le canvas peut être agrandi en plein écran.  
Après maximisation, il est possible de le faire glisser via les barres de défilement horizontale et verticale.  
La molette de la souris sert à changer d’étage lorsqu’il y en a plusieurs.
