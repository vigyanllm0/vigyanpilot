FROM python:3.11-slim

WORKDIR /app

# Install open-source native pipeline tools and healthcheck utilities.
RUN apt-get update && apt-get install -y --no-install-recommends \
    autodock-vina \
    bowtie2 \
    build-essential \
    ca-certificates \
    curl \
    ncbi-blast+ \
    openbabel \
    primer3 \
    samtools \
    tabix \
    vienna-rna \
    && rm -rf /var/lib/apt/lists/*

# Download GNINA binary (CNN docking scorer) — pre-built Linux binary from GitHub
RUN curl -fsSL https://github.com/gnina/gnina/releases/latest/download/gnina -o /usr/local/bin/gnina \
    && chmod +x /usr/local/bin/gnina

# Create non-root user
RUN groupadd -r vigyan && useradd -r -g vigyan -d /app -s /sbin/nologin vigyan

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY primerforge/ ./primerforge/
COPY secure_frontend.py .
COPY config/ ./config/
COPY frontend/ ./frontend/

# Permissions
RUN chown -R vigyan:vigyan /app && chmod -R 750 /app && chmod 640 /app/config/*.env 2>/dev/null || true

USER vigyan
EXPOSE 11436

ENV PYTHONUNBUFFERED=1
# Note: not using PYTHONWARNINGS=error because biopython pairwise2 emits
# deprecation warnings that would crash the app. Filter specific warnings instead.
ENV PYTHONWARNINGS=default
ENV PYTHONDONTWRITEBYTECODE=1
ENV BLAST_DB_BASE=/opt/postgres_data/blast_db
ENV BOWTIE2_INDEX_BASE=/opt/postgres_data/bowtie2
ENV CLINVAR_VCF_PATH=/opt/postgres_data/clinvar/clinvar.vcf.gz
ENV DBSNP_VCF_PATH=/opt/postgres_data/dbsnp/dbsnp.vcf.gz
ENV DFAM_REPEAT_PATH=/opt/postgres_data/dfam/dfam_repeats.tsv

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:11436/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:11436", "--workers", "1", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "primerforge.primer_server:create_app()"]
