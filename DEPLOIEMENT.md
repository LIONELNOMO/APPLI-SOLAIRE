# Déployer DimSolaire sur Render

Ce guide part d'un poste Windows, d'un compte GitHub et d'un compte
Render déjà créés. Comptez vingt minutes la première fois.

L'application tient en **un seul service** : FastAPI sert à la fois
l'API et l'interface compilée. Il n'y a donc rien à déployer séparément
pour le frontend.

---

## 1. Envoyer le code sur GitHub

Dans un terminal, à la racine du projet :

```bash
cd "C:/Users/user/Desktop/appli solaire"

git add -A
git commit -m "Version déployable"
git branch -M main
git remote add origin https://github.com/LIONELNOMO/APPLI-SOLAIRE.git
git push -u origin main
```

Si Git demande vos identifiants, GitHub n'accepte plus le mot de passe
du compte : il faut un **jeton d'accès personnel**, à créer sur
<https://github.com/settings/tokens>, portée `repo`. Collez ce jeton à
la place du mot de passe.

Vérifiez ensuite sur la page du dépôt que `Dockerfile`, `render.yaml` et
les dossiers `backend/` et `frontend/` sont bien présents, et que
`node_modules` est **absent**.

---

## 2. Choisir un mot de passe

L'application hébergée est protégée par un mot de passe unique, partagé
par tous ceux à qui vous donnez le lien. Choisissez-le maintenant, par
exemple `Dim2026!Yaounde`.

Ne le mettez jamais dans le dépôt : il se saisit uniquement dans
l'interface de Render, à l'étape suivante.

---

## 3. Créer le service sur Render

1. Sur <https://dashboard.render.com>, bouton **New**, puis **Blueprint**.
2. Choisissez le dépôt `LIONELNOMO/APPLI-SOLAIRE`. Render lit
   `render.yaml` et propose un service web et une base Postgres.
3. Render demande la valeur de `DIMSOLAIRE_MOT_DE_PASSE` : saisissez le
   mot de passe choisi à l'étape 2.
4. Validez. La première construction prend **cinq à dix minutes** :
   Render installe Node, compile l'interface, puis installe Python.

Si le bouton **Blueprint** est absent, créez un **Web Service** à la
main : dépôt `APPLI-SOLAIRE`, runtime **Docker**, plan **Free**, et
ajoutez les variables de la section 5 ci-dessous.

---

## 4. Vérifier

Render affiche une adresse de la forme
`https://dimsolaire.onrender.com`.

| Vérification | Résultat attendu |
|---|---|
| Ouvrir `/api/v1/health` | `{"statut":"ok",…}` sans mot de passe |
| Ouvrir la racine `/` | Le navigateur demande identifiant et mot de passe |
| Identifiant | N'importe lequel — il est ignoré |
| Mot de passe | Celui de l'étape 2 |

Une fois le mot de passe accepté, l'interface s'affiche et les quatre
onglets fonctionnent.

---

## 5. Les variables d'environnement

| Variable | Valeur | Rôle |
|---|---|---|
| `DIMSOLAIRE_MODE` | `web` | Sert l'interface et l'API ensemble |
| `DIMSOLAIRE_STATIC_DIR` | `/app/static` | Emplacement de l'interface compilée |
| `DIMSOLAIRE_MOT_DE_PASSE` | *votre mot de passe* | Protège l'accès |
| `DATABASE_URL` | *fournie par Render* | Connexion Postgres |
| `PORT` | *fournie par Render* | Port d'écoute imposé |

`DATABASE_URL` et `PORT` sont remplies automatiquement : n'y touchez pas.

---

## 6. Ce qu'il faut savoir sur le plan gratuit

**Le service s'endort après quinze minutes sans visite.** La visite
suivante attend **environ quarante secondes** le temps du réveil. Pensez
à ouvrir le lien quelques minutes avant une démonstration.

**La base Postgres gratuite expire au bout de trente jours.** Passé ce
délai, elle est supprimée et les projets enregistrés avec elle. Notez la
date de création. Les calculs, eux, continueront de fonctionner : le
moteur ne dépend pas de la base.

**Le disque du conteneur est effacé à chaque redéploiement.** C'est sans
effet ici, puisque les projets sont dans Postgres et non dans un fichier.

---

## 7. Mettre à jour l'application

```bash
git add -A
git commit -m "Description de la modification"
git push
```

Render détecte l'envoi et redéploie tout seul, en cinq à dix minutes.

---

## 8. En cas d'échec

Ouvrez l'onglet **Logs** du service sur Render.

| Message | Cause | Correctif |
|---|---|---|
| `no such table` | Tables non créées | Vérifier que `DATABASE_URL` est renseignée |
| `could not translate host name` | Base non liée | Recréer le lien vers `dimsolaire-db` |
| `Port scan timeout` | Mauvais port | Vérifier que `start.sh` est bien exécuté |
| `npm ci` échoue | `package-lock.json` absent | Vérifier qu'il est bien sur GitHub |
| Page blanche | Interface non compilée | Chercher `vite build` dans les logs |

---

## 9. Limites connues

**Le mot de passe est unique et partagé.** Il n'y a pas de comptes
individuels : qui a le mot de passe voit et modifie tous les projets. Les
comptes nominatifs (JWT, Argon2) sont prévus en phase 6 et ne sont pas
écrits à ce jour.

**Aucune migration de schéma n'existe.** Les tables sont créées au
premier démarrage. Si le schéma devait changer alors que la base contient
déjà des projets, il faudrait écrire des migrations Alembic : la création
automatique ne sait pas modifier une table existante.

**Le transport est chiffré par Render** (HTTPS), ce qui protège le mot de
passe en transit. L'authentification HTTP Basic ne serait pas acceptable
sur une liaison non chiffrée.
