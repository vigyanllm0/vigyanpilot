# Operations Runbook

## Service Down

1. Check systemd status: `sudo systemctl status vigyan`
2. Check logs: `sudo journalctl -u vigyan --since "10 min ago" --no-pager`
3. Restart: `sudo systemctl restart vigyan`
4. Verify: `curl -sf http://localhost:11436/health`

## Database Connection Refused

1. Check PostgreSQL: `pg_isready -h localhost -p 5432`
2. If down: `sudo systemctl restart postgresql` or `docker start vigyanpilot-postgres-1`
3. Check connection pool exhaustion in logs
4. If persistent: verify `DATABASE_URL` in `.env`

## Redis Connection Failed

1. Check Redis: `redis-cli ping`
2. If down: `sudo systemctl restart redis`
3. Fallback: the app falls back to in-memory cache automatically
4. Verify: check logs for "Redis unavailable, using memory fallback"

## Disk Space Full

1. Check usage: `df -h /`
2. Clean logs: `sudo journalctl --vacuum-size=50M`
3. Clean Docker: `docker system prune -af`
4. Clean apt cache: `sudo apt-get clean -y`
5. Expand volume if on cloud (AWS EBS, etc.)

## High Error Rates

1. Check Sentry dashboard for new error clusters
2. If no Sentry: `sudo journalctl -u vigyan --since "1 hour ago" | grep -i error`
3. Identify error type: transient (retry) vs persistent (rollback)
4. Rollback procedure: see "Deploy Failed" below

## Payment Webhook Failures

1. Check Razorpay dashboard → Webhooks tab
2. Verify webhook secret in `.env` matches Razorpay dashboard
3. Check server logs for signature verification errors
4. Manually replay failed webhooks from Razorpay dashboard

## SSL Certificate Expired

1. Check expiry: `echo | openssl s_client -connect vigyanllm.in:443 2>/dev/null | openssl x509 -noout -dates`
2. Renew: `sudo certbot renew --nginx`
3. If certbot fails: `sudo certbot certonly --nginx -d vigyanllm.in -d www.vigyanllm.in`
4. Reload nginx: `sudo systemctl reload nginx`

## High Memory Usage

1. Check: `free -h` and `ps aux --sort=-%mem | head -10`
2. If gunicorn workers leaked: `sudo systemctl restart vigyan`
3. Tune workers: edit `deploy/vigyan.service` → `--workers` (rule of thumb: 2 * CPU cores + 1)
4. If persistent: check for memory leaks in request handlers

## Deploy Failed

1. Check CI/CD logs in GitHub Actions
2. If deploy SSH failed: SSH in and check `~/vigyanpilot` state
3. Rollback:
   ```bash
   cd ~/vigyanpilot
   git log --oneline -5          # find last good commit
   git reset --hard <good-sha>
   source .venv/bin/activate
   pip install -r requirements.txt --quiet
   python deploy/migrations/migrate.py
   sudo systemctl restart vigyan
   ```
4. Verify: `curl -sf http://localhost:11436/health`

## Database Migration Failed

1. Check which migration failed in deploy logs
2. Connect to DB: `psql $DATABASE_URL`
3. Check applied: `SELECT * FROM schema_version ORDER BY version;`
4. If partially applied: manually fix the broken statement, then mark as applied:
   ```sql
   INSERT INTO schema_version (version, name) VALUES (<version>, '<name>');
   ```
5. If corrupt: restore from last backup, then re-run `python deploy/migrations/migrate.py`
