# Deploy to Google Cloud Run in Mumbai (asia-south1)

One container, autoscaling from zero, India region for data localisation. About 10 minutes.

```bash
# 1. Project and region
gcloud config set project YOUR_PROJECT
gcloud config set run/region asia-south1
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

# 2. Secrets (the master key never sits in code or env files)
python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())" | gcloud secrets create accel-master-key --data-file=-
printf '%s' "$YOUR_LLM_KEY" | gcloud secrets create accel-llm-key --data-file=-      # optional

# 3. Database: Neon or Supabase (free) or Cloud SQL for Postgres in asia-south1
#    DATABASE_URL looks like postgresql://user:pass@host/udyam?sslmode=require

# 4. Build and deploy from the repo root
gcloud run deploy udyam-digital --source . --allow-unauthenticated \
  --min-instances 1 --max-instances 10 --memory 1Gi --cpu 1 \
  --set-env-vars ENVIRONMENT=demo,JUDGE_MODE=true,LLM_PROVIDER=anthropic,CORS_ORIGINS="$APP_URL",PUBLIC_URL="$APP_URL",DATABASE_URL="$DATABASE_URL" \
  --set-secrets MASTER_KEY_B64=accel-master-key:latest,LLM_API_KEY=accel-llm-key:latest,SARVAM_API_KEY=accel-sarvam-key:latest
```

Notes
- `--min-instances 1` keeps one instance warm during judging (no cold start).
- Without `DATABASE_URL` the app uses SQLite inside the container: fine for a demo, reset on each deploy.
- For document storage in a bucket, add `STORAGE_BACKEND=gcs,STORAGE_BUCKET=your-bucket` (bucket in asia-south1). Files are encrypted before upload either way.
- Several instances share live tracker events when `REDIS_URL` points to Memorystore or Upstash.
- WhatsApp: point the Meta webhook at `https://YOUR_URL/api/whatsapp/webhook` with `WHATSAPP_VERIFY_TOKEN`, and set `WHATSAPP_TOKEN` and `WHATSAPP_PHONE_ID`.

Environments
- `ENVIRONMENT=demo` is the judge demo: judge mode and demo staff accounts allowed, synthetic data. Give it its own project.
- `ENVIRONMENT=prod` refuses to start unless judge mode is off, `STAFF_ACCOUNTS`, `MASTER_KEY_B64`, `CORS_ORIGINS` and (with WhatsApp) `WHATSAPP_APP_SECRET` are set, and mock adapters are off.
- Infrastructure as code for both: `infra/terraform/` (Cloud Run, Cloud SQL with backups to Delhi, Secret Manager, Cloud KMS, CMEK bucket). CI deploys the demo with a no-traffic canary first.

LLM options (any one): `LLM_PROVIDER=anthropic` (default model claude-opus-5-5), `gemini` (default gemini-flash-latest), or `openai` with `LLM_BASE_URL` for any OpenAI-compatible API (for example Groq). Set `LLM_MODEL` to override.
