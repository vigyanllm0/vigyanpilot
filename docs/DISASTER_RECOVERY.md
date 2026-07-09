# VigyanLLM Disaster Recovery & High Availability Plan

## 1. Overview
This Disaster Recovery (DR) runbook outlines the architectural controls and operational procedures required to restore the VigyanLLM platform in the event of an infrastructure failure, database corruption, or regional outage.

## 2. Infrastructure Architecture
To prevent single points of failure, the production deployment should adhere to the following architecture:
- **Load Balancing**: Use Nginx or an application load balancer (ALB) to distribute traffic across multiple Gunicorn/Uvicorn worker instances.
- **Database High Availability**: 
  - Deploy PostgreSQL in a Multi-AZ configuration using a managed service (e.g., AWS RDS, GCP Cloud SQL).
  - Implement PgBouncer or native connection pooling to prevent connection exhaustion under heavy load.
- **Cache & Queue**: Use a managed Redis cluster (e.g., ElastiCache) for Celery task queuing and rate-limiting data.

## 3. Backup Strategy
- **Database Backups**: 
  - Automated daily snapshots retained for a minimum of 14 days.
  - Continuous WAL (Write-Ahead Logging) archiving for Point-In-Time Recovery (PITR) up to 5 minutes of RPO (Recovery Point Objective).
- **Offsite Storage**: Local backup scripts (`infra/scripts/backup_daily.sh`) must securely encrypt all backups (using AES-256 or GPG) and upload them to immutable offsite storage (e.g., AWS S3 with Object Lock).

## 4. Recovery Procedures
In the event of a critical failure:
1. **Identify the Failure Domain**: Determine if the outage is at the application layer, database layer, or regional infrastructure.
2. **Application Failure**: 
   - Ensure Docker containers have restart policies (`restart: always`).
   - If EC2/Compute instance fails, spin up a new instance using the automated CI/CD deployment pipeline or Terraform scripts.
3. **Database Failure**:
   - For managed databases, initiate an automatic failover to the standby replica.
   - For corrupted data, restore the most recent uncorrupted automated snapshot or use PITR.
4. **Post-Recovery**: Verify application health (`GET /health`), validate database connections, and confirm Redis queue functionality.

## 5. Security & Observability
- All backups must be fully encrypted at rest to prevent the leakage of PII or API credentials.
- Application and database logs must be aggregated in a centralized logging system (e.g., ELK stack, Datadog) to ensure post-incident forensics are possible even if the primary instance is lost.
