# DimSolaire

Logiciel de dimensionnement de centrale photovoltaïque et d'injection au
réseau, pour la zone d'étude de **Yaoundé Ouest** (Cameroun).

Une seule base de code, deux formes de livraison : une application PC
Windows utilisable **sans connexion internet**, et une application web.

| Document | Contenu |
|---|---|
| [`CAHIER_DE_CHARGES.md`](CAHIER_DE_CHARGES.md) | Métier : exigences, formules F-01 à F-30, vérifications, catalogues, cas de référence |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Technique : architecture, pile, API, design system, build, état de la recette |

---

## Démarrage rapide

### Première installation

```bat
scripts\installer.bat
```

Installe l'environnement Python, les dépendances du moteur et de
l'interface, puis lance les tests pour vérifier que tout fonctionne.

**Prérequis** : Python 3.12 et Node.js 20 ou plus récents.

### Lancer le logiciel

```bat
DimSolaire.bat
```

Démarre les deux serveurs — le moteur de calcul sur le port 8000 et
l'interface sur le port 5173 — puis ouvre le navigateur. Fermez la fenêtre
pour arrêter les deux.

### Version autonome, sans Python ni Node.js

```bat
scripts\build_autonome.bat     :: une seule fois
DimSolaire-autonome.bat        :: à chaque utilisation
```

Compile le moteur en un exécutable unique qui sert aussi l'interface. Pour
distribuer sur un poste sans outils de développement, copiez :

```
DimSolaire-autonome.bat
backend\dist\dimsolaire-api.exe
frontend\dist\
```

---

## Les quatre onglets

| Onglet | Question traitée | Formules |
|---|---|---|
| 1. Potentiel solaire | Combien de soleil la zone reçoit-elle ? | F-01 à F-04 |
| 2. Bilan énergétique | Combien d'énergie la zone consomme-t-elle ? | F-05 à F-08 |
| 3. Dimensionnement | Quel matériel, et comment le câbler ? | F-09 à F-25 |
| 4. Injection | Comment injecter l'énergie sur le réseau ? | F-26 à F-30 |

---

## Développement

```bash
# Moteur de calcul
cd backend
.venv\Scripts\activate
uvicorn app.main:create_app --factory --reload --port 8000

# Interface
cd frontend
npm run dev
```

Documentation de l'API en marche : <http://127.0.0.1:8000/docs>

### Contrôles

```bash
cd backend
ruff check app/ tests/        # lint
ruff format app/ tests/       # formatage
mypy app/engine/              # typage strict du moteur
pytest -q                     # 98 tests
pytest --cov=app/engine       # couverture

cd frontend
npm run lint
npm run build
```

### Recettes

```bash
cd backend
python verif.py              # relevé des cas de référence R-01 à R-10
python simulation.py         # projet complet contre l'API en marche
python verif_sidecar.py      # recette de l'exécutable compilé
python verif_autonome.py     # recette de la version autonome
```

---

## Principes de conception

| Code | Principe |
|---|---|
| P1 | Moteur de calcul unique, en Python pur, sans état ni entrées-sorties |
| P2 | Projet autoporteur : les fiches des équipements sont copiées dans le projet |
| P3 | Ne jamais bloquer l'utilisateur : une valeur hors plage produit un message, jamais un plantage |
| P4 | Unités explicites dans les noms de variables, conversions centralisées |
| P5 | Traçabilité : chaque formule porte un identifiant `F-xx` cité dans le code, les tests et le rapport |
| P6 | Une seule base de code pour les deux formes de livraison |

La route de calcul ne renvoie **jamais** d'erreur HTTP pour une valeur
métier : les problèmes remontent comme messages dans la réponse, avec un
code (`PV-E06`, `OND-A03`…), un niveau et une suggestion de correction.

---

## État du projet

Le moteur, l'API, le rapport PDF et l'interface sont écrits et testés.
Les points non vérifiés sont listés au §16 d'[`ARCHITECTURE.md`](ARCHITECTURE.md) :
l'installateur Tauri n'a jamais été compilé, et l'image Docker jamais
construite.

**La version web n'a pas d'authentification** : les comptes utilisateurs
sont prévus en phase 6. Ne pas l'exposer sur internet avant.

Trois arbitrages attendent la réponse de l'encadrant (Q-01, Q-08, Q-09).
Ils sont traités comme des paramètres : changer un avis ne demandera
qu'une modification de configuration, pas de réécriture.
