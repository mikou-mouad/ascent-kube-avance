# La présentation

69 slides : pour chaque chapitre, l'incident chez Croustino, la solution, le concept (schémas et code), puis le TP.

## Présenter

- **En ligne (version de référence) :** l'artifact claude.ai du formateur, avec le mode présentation, les notes et l'export PDF / PowerPoint.
- **Hors ligne :** ouvrez `index.html` dans un navigateur.

| Touche | Action |
|--------|--------|
| → / Espace / clic | slide suivante |
| ← | slide précédente |
| N | afficher les notes du formateur |
| F | plein écran |

Les polices viennent de Google Fonts : sans Internet, le navigateur utilise des polices de remplacement.
Les icônes sont remplacées par des symboles simples.

## Les fichiers

- `deck.json` : l'ordre des slides et les chapitres
- `slides/<id>.html` : une slide par fichier, avec les notes du formateur dans `<aside>`
- `construire.py` : assemble `index.html` à partir des slides

Après une modification d'une slide :

```bash
python presentation/construire.py
```
