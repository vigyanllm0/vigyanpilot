# VigyanLLM Security & Hardening Guide

## Overview
This document outlines the security controls, authentication mechanisms, and infrastructural hardening applied to the VigyanLLM Primer/Probe Design Platform.

## 1. Authentication & Identity
- **Passwords**: User and admin passwords are hashed using **bcrypt** with a secure work factor. SHA-256 (unsalted) has been entirely deprecated.
- **Tokens**: JWT and session tokens are generated using cryptographically secure secrets (`PRIMERFORGE_SECRET`).
- **Sessions**: The SQLite and PostgreSQL session stores are protected by `threading.RLock` and transaction locks to prevent concurrency bugs and data races.
- **Admin RBAC**: Administrative endpoints strictly require verified tokens on the server-side; edge middleware string checks have been fortified with backend verification.

## 2. Secrets Management
- All secrets (Razorpay keys, API keys, database credentials) are stored strictly in `.env`.
- `.env` is explicitly added to `.gitignore`.
- Live Razorpay keys and admin credentials previously committed to the codebase have been **rotated and purged**.

## 3. Threat Protection & Input Validation
- **XSS Prevention**: 
  - All SVG uploads are rigorously sanitized using the `defusedxml` library to prevent XML External Entity (XXE) and embedded script attacks.
  - HTML content (from CMS or user input) is sanitized using `bleach` with a strict tag/attribute whitelist before rendering.
- **Path Traversal & Command Injection**: User inputs are strictly validated. Shell execution is heavily restricted and sanitized.

## 4. Payment Integrity
- **Server-Side Verification**: Razorpay payments are validated via HMAC signature **and** confirmed via a server-to-server API call (`GET /payments/{id}`) to ensure the payment was actually captured, preventing forged HMAC claims.
- **Atomic Operations**: Financial transactions and token credits use atomic test-and-set database operations to prevent race conditions and double-crediting.
- **Webhook Security**: A dedicated `RAZORPAY_WEBHOOK_SECRET` is enforced for webhook signature validation.

## 5. Observability & Auditing
- System actions (logins, payments, data requests) are persistently recorded in the `audit_logs` table.
- All timestamps across the platform enforce UTC (`datetime.now(timezone.utc)`) and use PostgreSQL `TIMESTAMPTZ` for absolute chronological integrity.
- All 61+ bare/silent exception handlers (`except Exception: pass`) have been removed or updated to properly log the suppressed exceptions, ensuring full system observability.
