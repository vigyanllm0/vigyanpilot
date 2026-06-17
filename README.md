# VigyanLLM Primer Design Platform

Production-grade, India-first primer and probe design platform with automated 22-step biophysical validation pipeline.

## Quick Start

### Development Mode

```bash
# Start PostgreSQL (Postgres.app or Docker)
# Start Redis (for Celery in production)
# Start backend API
cd /Users/macbookpro/Desktop/vigyanpilot
source .venv/bin/activate
python -m primerforge.primer_server

# Start frontend (separate terminal)
cd /Users/macbookpro/Desktop/vigyanpilot
python -m http.server 8080
```

Access at:
- Frontend: http://localhost:8080/primer.html
- Backend API: http://localhost:11436
- Health check: http://localhost:11436/health

## Production Setup

### Celery + Redis (Background Task Queue)

In production, pipeline runs execute asynchronously via Celery to avoid blocking HTTP requests.

**Start Redis:**
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using Homebrew (macOS)
brew install redis
brew services start redis
```

**Start Celery Worker:**
```bash
cd /Users/macbookpro/Desktop/vigyanpilot
source .venv/bin/activate
celery -A primerforge.celery_app worker --loglevel=info --concurrency=4
```

**Start Celery Beat (for scheduled tasks, if needed):**
```bash
celery -A primerforge.celery_app beat --loglevel=info
```

**Environment Variables Required:**
```bash
# Add to .env or export
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Database

**PostgreSQL Setup:**
```bash
# Using Postgres.app (macOS)
# Download from https://postgresapp.com/
# Start Postgres.app, initialize PostgreSQL 18.4

# Using Docker
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=vigyanpilot_app \
  -e POSTGRES_PASSWORD=vigyanpilot_local_2026 \
  -e POSTGRES_DB=vigyanpilot_db \
  postgres:18-alpine
```

**Database URL (already in .env):**
```
DATABASE_URL=postgresql://vigyanpilot_app:vigyanpilot_local_2026@localhost:5432/vigyanpilot_db
```

## Configuration

### NCBI API Key (Optional but Recommended)

To increase NCBI API rate limit from 3 req/sec to 10 req/sec:

1. Get your free API key from: https://www.ncbi.nlm.nih.gov/account/
2. Add it to `config/ncbi_api_key.txt`:
   ```
   YOUR_NCBI_API_KEY_HERE
   ```

### Razorpay Payment Keys

Live keys are already configured in `.env`. For testing, use test keys from Razorpay dashboard.

## Architecture

- **Backend:** Python/Flask on port 11436
- **Frontend:** Static HTML/CSS/JS on port 8080
- **Database:** PostgreSQL 18.4
- **Task Queue:** Celery + Redis (production), synchronous fallback (dev)
- **Payment:** Razorpay (UPI, cards, net banking)

## Known Issues & Solutions

### IP Lock for Mobile/Dynamic IP Users

Users who change networks (mobile data, VPN, office WiFi) may be locked out due to IP-bound account security.

**Solution:** Admin can unlock IP via endpoint:
```bash
POST /api/admin/users/<user_id>/unlock-ip
Authorization: Bearer <admin_token>
```

### Celery Not Running

If Celery is not running, pipeline runs fall back to synchronous execution (dev mode). This blocks the HTTP request thread for the duration of the pipeline.

**Solution:** Start Celery worker as shown above.

## Development

### Running Tests

```bash
cd /Users/macbookpro/Desktop/vigyanpilot
pytest tests/
```

### Code Structure

- `primerforge/engine/steps/` - 22-step pipeline implementation
- `primerforge/pg_auth_routes.py` - Authentication endpoints
- `primerforge/pg_payment_routes.py` - Payment integration
- `primerforge/reports_routes.py` - Report history & academic/referral features
- `primer.html` - Main frontend application

## Support

For issues or questions, contact: contact@vigyanllm.in
