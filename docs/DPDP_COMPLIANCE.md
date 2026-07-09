# DPDP Act Compliance Framework

## Overview
This document details how the VigyanLLM platform complies with the Digital Personal Data Protection (DPDP) Act of India.

## 1. Notice and Consent (§6, §7)
- **Account Registration**: Users are explicitly presented with a consent checkbox during registration. Account creation is blocked unless the user actively consents to the Terms of Service and Privacy Policy.
- **Cookie Consent**: The platform features a Cookie Consent Banner on the frontend. Non-essential tracking scripts, including Google Tag Manager (GTM) and Google Analytics, are strictly gated and do not load until the user grants explicit cookie consent.

## 2. Data Principal Rights (§12)
The platform exposes dedicated API endpoints to fulfill the statutory rights of the Data Principal:
- **Right to Correction & Erasure (§12(3), §12(4))**: 
  - `DELETE /api/auth/account`: Allows users to permanently delete their account. This triggers a cascading deletion/anonymization of all PII, pipeline reports, tokens, and sessions associated with the user.
  - `PUT /api/auth/profile`: Allows users to update and correct their personal information.
- **Right to Data Portability (§12(5))**: 
  - `GET /api/auth/export`: Provides users with a downloadable JSON archive containing all their personal data, pipeline run history, payments, and generated reports.

## 3. Data Minimization & Retention
- **PII Scrubbing**: Logs have been sanitized to remove raw email addresses and other PII, replacing them with obfuscated IDs where possible.
- **Retention**: Data retention policies (such as purging audit logs older than 90 days and removing inactive accounts after 2 years) should be enforced via automated background cron jobs.

## 4. Security Safeguards (§8)
- The platform operates strictly over HTTPS in production.
- Databases utilize robust connection pooling, parameterized SQL queries, and encryption for sensitive pipeline results.
- Robust auditing logs all critical data access and modifications to maintain a verifiable trail of data processing activities.
