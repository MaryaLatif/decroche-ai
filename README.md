# Onboarding commerce — agent IA

Le commerçant retrouve son établissement (Google Places), l'app collecte son catalogue et ses horaires,
puis un agent Claude répond aux clients et prépare des demandes de commande.

## Lancer en local

Backend (Python, `uv`) :

```bash
cd backend
cp .env.example .env   # puis renseigner les clés
uv sync
uv run uvicorn main:app --reload --port 8080
```

Frontend (React + Vite) :

```bash
cd frontend
npm install
npm run dev
```

Ouvrir http://localhost:5173.

## Données

Les fichiers par commerce sont écrits dans `backend/data/businesses/<place_id>/` (ignoré par Git).