# web-clase · SySM Quiz

Flask app de tests para *Síntesis y Simulación de Mecanismos* con login y leaderboard
respaldados en PostgreSQL.

## Variables de entorno

| Variable        | Valor                                          |
| --------------- | ---------------------------------------------- |
| `DATABASE_URL`  | URL de PostgreSQL (`postgresql://user:pass@host:5432/db`) |
| `SECRET_KEY`    | Cadena aleatoria para sesiones de Flask        |
| `PORT`          | Puerto HTTP (Railway / Cloud Run lo inyectan)  |

## Despliegue en Railway

1. Conecta el repo en railway.com → **Deploy from GitHub**.
2. Añade un servicio PostgreSQL y enlaza la variable `DATABASE_URL`.
3. Define `SECRET_KEY` con una cadena aleatoria.
4. Railway usa automáticamente el `Dockerfile` (o `railway.json`).
5. Healthcheck en `/healthz`.

## Despliegue en Google Cloud Run

```bash
gcloud run deploy web-clase --source . \
    --region europe-west1 \
    --allow-unauthenticated \
    --set-env-vars="DATABASE_URL=postgresql://...,SECRET_KEY=..."
```

## Desarrollo local

```bash
pip install -r requirements.txt
$env:DATABASE_URL = "sqlite:///sysm_local.db"   # o tu Postgres
python app.py
```
