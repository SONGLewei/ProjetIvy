1. Creation des etages  
Après avoir lance `main.py`, l'utilisateur doit cliquer en haut a gauche pour creer un nouvel etage.  
Le premier etage est automatiquement nomme "Floor 0".  
Un clic droit sur un etage permet de renommer l'etage ou de definir sa hauteur.

2. Ajout de nouveaux etages  
Chaque nouvel etage est ajoute au-dessus de l'etage selectionne.  
Actuellement, la suppression des etages n’est pas possible (fonctionnalite non prevue).

3. Outils de dessin  
Sur chaque etage, l'utilisateur peut dessiner :
- Des murs (noir, par defaut)
- Des fenêtres (violet clair)
- Des portes (marron)
- Quatre types de gaines de ventilation (avec couleurs differentes)

Après avoir clique sur l’outil “ventilation”, un menu permet de choisir le type de gaine (couleur + fonction).  
L’utilisateur doit ensuite renseigner le nom, le diamètre et le debit d’air pour chaque gaine (les dialogues s’affichent automatiquement).

4. Affichage des informations  
Après la creation d’une gaine, un survol avec la souris de plus d’1 seconde affiche les informations suivantes :  
- Nom  
- Diamètre  
- Debit  
- Fonction

5. Gomme  
Après avoir selectionne l’outil gomme, un simple clic sur un element du dessin le supprime.

6. Securite d’interaction  
Un simple clic sur le canvas sans avoir selectionne d’outil ne declenche aucune action.

7. Aide visuelle  
En haut a gauche, une boussole et une règle indiquent les directions (N/E/S/O) et une echelle de 2 mètres.

8. Contrôle du canvas  
Le canvas peut être agrandi en plein ecran.  
Après maximisation, il est possible de le faire glisser via les barres de defilement horizontale et verticale.  
La molette de la souris sert a changer d’etage lorsqu’il y en a plusieurs.
