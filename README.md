# Système de Conception VMC (Ventilation Mécanique Contrôlée)

## Présentation

Cette application est un outil de conception et de visualisation pour les systèmes de ventilation mécanique contrôlée (VMC) dans les bâtiments. Elle permet aux utilisateurs de créer des plans de bâtiments multi-étages, de placer des murs, fenêtres, portes, et de concevoir des systèmes de ventilation complets avec gaines et plénums.

L'application utilise une architecture Modèle-Vue-Contrôleur (MVC) pour une séparation claire entre la logique métier, l'interface utilisateur et le traitement des données.

## Prérequis

- Python 3.6 ou supérieur
- Bibliothèque PIL/Pillow pour le traitement d'images
- Tkinter (généralement inclus avec Python)

## Installation

1. Clonez le dépôt ou téléchargez les fichiers sources
2. Installez les dépendances requises :
   ```
   pip install pillow
   ```

## Exécution

Pour lancer l'application, exécutez la commande suivante depuis le répertoire racine du projet :

```
python main.py
```

## Structure du Projet

```
ProjetIvy/
├── controller/          # Logique de l'application
│   └── controller.py    # Contrôleur principal
├── model/               # Classes de données
│   ├── door.py          # Modèle pour les portes
│   ├── floor.py         # Modèle pour les étages
│   ├── object.py        # Classe de base abstraite
│   ├── plenum.py        # Modèle pour les plénums
│   ├── vent.py          # Modèle pour les gaines
│   ├── wall.py          # Modèle pour les murs
│   └── window.py        # Modèle pour les fenêtres
├── view/                # Interface utilisateur
│   ├── graphical_view.py # Implémentation de l'UI
│   ├── tooltip.py       # Composant pour les infobulles
│   └── photos/          # Icônes et images de l'UI
├── ivy/                 # Système d'événements
│   ├── __init__.py      # Initialisation du package
│   └── ivy_bus.py       # Bus d'événements publish-subscribe
├── floors.json          # Données de projet (étages)
├── plenums.json         # Données de projet (plénums)
├── main.py              # Point d'entrée de l'application
└── README.md            # Ce fichier
```

## Architecture

L'application est construite selon le modèle MVC (Modèle-Vue-Contrôleur) :

- **Modèle** : Les classes dans le dossier `model/` représentent les données et la logique métier.
- **Vue** : Les classes dans `view/` gèrent l'interface utilisateur et les interactions.
- **Contrôleur** : `controller.py` orchestre les interactions entre le modèle et la vue.

La communication entre les composants est assurée par un bus d'événements personnalisé (`ivy_bus`) qui implémente le pattern Observer.

## Fonctionnalités

### Gestion des Étages
- Création et gestion de plans multi-étages
- Possibilité de définir la hauteur de chaque étage
- Visualisation "pelure d'oignon" des étages adjacents
- Duplication d'étages

### Dessin de Plans
- Outils de dessin pour murs, fenêtres et portes
- Aide à l'alignement pour les éléments structurels
- Échelle et coordonnées pour faciliter la conception

### Système de Ventilation
- Placement de gaines de ventilation avec spécifications techniques
- Configuration de plénums avec débit d'air et dimensions
- Calcul automatique des besoins en ventilation
- Rapports et résumés du système de ventilation

### Gestion de Projet
- Sauvegarde et chargement de projets
- Exportation de données techniques

## Guide d'Utilisation

### 1. Création des Étages
- Lancez l'application via `main.py`
- Cliquez en haut à gauche pour créer un nouvel étage
- Le premier étage est automatiquement nommé "Étage 0"
- Un clic droit sur un étage permet de le renommer ou de définir sa hauteur

### 2. Ajout de Nouveaux Étages
- Chaque nouvel étage est ajouté au-dessus de l'étage sélectionné
- La duplication d'étage est possible via le menu contextuel (clic droit)

### 3. Outils de Dessin
Sur chaque étage, vous pouvez dessiner :
- Des murs (noir, par défaut)
- Des fenêtres (violet clair)
- Des portes (marron)
- Quatre types de gaines de ventilation (avec couleurs différentes)

### 4. Gestion des Gaines
- Après avoir cliqué sur l'outil "ventilation", un menu permet de choisir le type de gaine
- Renseignez le nom, le diamètre et le débit d'air pour chaque gaine
- Un survol avec la souris affiche les informations techniques

### 5. Création de Plénums
- Sélectionnez l'outil plenum
- Définissez sa position, dimensions et caractéristiques techniques
- Les plénums peuvent être reliés aux gaines de ventilation

### 6. Navigation
- Molette de souris pour changer d'étage
- Barres de défilement pour naviguer dans le canvas
- Boussole et règle d'échelle pour l'orientation spatiale

### 7. Gestion de Projet
- Bouton Sauvegarder pour enregistrer le projet
- Bouton Importer pour charger un projet existant

## Limitations Connues
- La suppression des étages n'est pas implémentée
- Pas de fonctionnalité d'annulation (undo/redo)
- L'application ne crée pas automatiquement de rapports PDF

## Technologies Utilisées
- Python 3 pour le langage de programmation
- Tkinter pour l'interface graphique
- PIL/Pillow pour le traitement d'images
- JSON pour le stockage des données

## Contribuer
Pour contribuer au projet, veuillez suivre les bonnes pratiques de codage :
- Respecter l'architecture MVC
- Documenter les nouvelles fonctionnalités
- Maintenir la séparation des préoccupations entre les modules
