# Navigabilité V2 — Coquille vide (Django + Postgres)

**Fonctionnalités incluses :**
- Authentification par identifiant/mot de passe (Django)
- Page **Profil** (lecture seule pour l’instant)
- Rôles utilisateurs : `pilote`, `technicien`, `proprietaire`, `camo`, `admin`, `superadmin`
- Chaque utilisateur est rattaché à une **Organisation**
- **Super administrateur** : CRUD Organisations
- **Admin & Super admin** : création d’utilisateurs
- Docker + docker-compose (PostgreSQL)

## Démarrage rapide (Docker)
```bash
cd app
docker compose up --build
```
Le site sera disponible sur http://localhost:8000

### Créer un super utilisateur (pour accéder à /admin/ et initialiser le système)
Dans un autre terminal :
```bash
cd app
docker compose exec web python manage.py createsuperuser
```

## Sans Docker (en local, Python 3.12+)
```bash
cd app
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DJANGO_SECRET_KEY="change-me"
export DJANGO_DEBUG=1
export DB_NAME=navdb DB_USER=navuser DB_PASSWORD=navpass DB_HOST=localhost DB_PORT=5432
python manage.py migrate
python manage.py runserver
```

## Routes clés
- `/login/` et `/logout/`
- `/profile/` (tout utilisateur connecté)
- `/organizations/` (superadmin uniquement)
- `/organizations/create/` (superadmin uniquement)
- `/organizations/<id>/edit/` (superadmin uniquement)
- `/users/create/` (admin & superadmin)

## Notes
- Le modèle utilisateur est personnalisé (`accounts.User`) pour inclure `role` et `organization`.
- En création d’utilisateur par un **admin** (non superadmin), l’organisation de l’utilisateur créé est automatiquement forcée à celle de l’admin.
- L’interface d’administration Django est disponible via `/admin/`.
- **Production** : désactivez DEBUG, fixez `ALLOWED_HOSTS`, utilisez un secret robuste et une stack serveur (gunicorn + nginx), migrations gérées, etc.
