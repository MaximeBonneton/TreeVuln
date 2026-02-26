# Roadmap TreeVuln — Post-audit sécurité

## Corrections appliquées

| ID | Faille | Sévérité | Statut |
|----|--------|----------|--------|
| C-1 | Auth bypass (ADMIN_API_KEY vide) | Critique | Done |
| C-2 | Endpoints /evaluate sans auth | Critique | Done |
| C-3 | TOCTOU SSRF (DNS rebinding) | Critique | Done |
| C-4 | Configuration TLS (nginx.conf, Dockerfile, entrypoint) | Critique | Done |
| H-1 | ReDoS via regex utilisateur | Haute | Done |
| H-2 | CRLF header injection webhooks | Haute | Done |
| H-3 | Payload ingestion illimité | Haute | Done |
| H-4 | Chiffrement secrets webhook en BDD (crypto.py + services) | Haute | Done |
| H-5 | Auth session cookie (suppression VITE_ADMIN_API_KEY) | Haute | Done |
| H-6 | Credentials DB hardcodées en fallback | Haute | Done |
| H-7 | Port frontend exposé sur 0.0.0.0 | Haute | Done |
| H-8 | Password DB faible dans .env.example | Haute | Done |
| H-9 | Rôle PostgreSQL dédié (script + .env) | Haute | Done |

## A vérifier / finaliser

1. **Vérifier compilation TypeScript frontend** — valider que les modifications frontend compilent (`npx tsc --noEmit`), notamment `App.tsx` avec le nouveau composant `Login`
2. **Tester le build Docker complet** — `docker compose up -d --build` pour valider TLS auto-signé, le rôle DB, et l'auth session
3. **Erreur TS pré-existante** — `IngestConfigDialog.tsx:171` a un type `string | undefined` non géré (antérieur à l'audit)

## Failles moyennes (à planifier)

| # | Description | Fichier(s) | Statut |
|---|-------------|------------|--------|
| M-1 | Clés API d'ingestion en clair en BDD | `crypto.py` + `ingest_service.py` + `ingest.py` + schemas | **Done** |
| M-2 | Tâches webhook async non bornées (risque OOM) | `webhook_dispatch.py` + `evaluate.py` + `ingest.py` — sémaphore (20 max) | **Done** |
| M-3 | Pagination sans limite haute (`limit=999999999`) | Routes assets/webhooks/logs — `Query(ge=1, le=1000)` | **Done** |
| M-4 | Filename non sanitisé dans les imports | Routes assets/evaluate — valider l'extension et le nom | |
| M-5 | `eval()` dans le moteur de formule | `engine/nodes.py` — bien protégé par AST, mais envisager `simpleeval` | |
| M-6 | Race conditions store Zustand (pas d'AbortController) | `treeStore.ts` — annuler les requêtes en cours au changement d'arbre | |
| M-7 | Builds Docker non reproductibles | Ajouter `package-lock.json`, utiliser `npm ci`, pinner les images | |
| M-8 | Pas de limites ressources conteneurs | `docker-compose.yml` — ajouter `mem_limit`, `cpus` | |
| M-9 | Conteneur frontend en root | Dockerfile frontend — le `nginx-user` est créé mais la directive `USER` manque (nginx a besoin de root pour le port 443, à résoudre avec `setcap` ou port > 1024) | |
| M-10 | Single worker uvicorn | Ajouter gunicorn avec 2-4 workers ou `--workers` | |

## Failles basses / améliorations (backlog)

| # | Description |
|---|-------------|
| B-1 | Rate-limiting par IP sur les endpoints d'ingestion (au-delà du rate-limit nginx) |
| B-2 | Rotation automatique des clés API d'ingestion |
| B-3 | Logs d'audit des actions admin (qui a modifié quoi) |
| B-4 | Migration Alembic formelle (au lieu de `create_all` au startup) |
| B-5 | Healthcheck HTTPS dans docker-compose (actuellement HTTP) |
| B-6 | CSP `connect-src` à restreindre aux domaines webhook autorisés |
| B-7 | Ajouter `Secure` flag explicite sur le cookie de session en production |
| B-8 | Tests unitaires pour `crypto.py`, `auth.py`, et la nouvelle auth session dans `deps.py` |
| B-9 | Expiration/nettoyage automatique des logs webhook et ingestion anciens |
| B-10 | Support certificats TLS fournis par l'utilisateur (volume mount au lieu d'auto-signé) |
| B-11 | Documentation déploiement production (guide de hardening) |

## Ordre de priorité recommandé

1. ~~**Valider le build** — tsc + docker compose~~ ✅
2. ~~**M-1** — chiffrer les clés d'ingestion (même pattern que webhooks)~~ ✅
3. ~~**M-2 + M-3** — borner les tâches async et la pagination~~ ✅
4. **M-4** — sanitiser les noms de fichiers dans les imports
5. **M-7** — reproductibilité des builds (lockfiles)
6. **B-8** — tests pour les nouveaux modules de sécurité
7. Le reste par ordre d'impact
