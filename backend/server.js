/**
 * VigyanLLM CMS Auth Server (Node.js)
 * =====================================
 * Lightweight email-based registration + verification flow for the CMS.
 *
 * Security hardening (SEC-01 / BUG-01 FIX):
 *   PREVIOUSLY: SHA-256 unsalted hash — trivially crackable with rainbow tables.
 *   FIX: bcrypt with cost factor 12 — salted, slow, industry standard.
 *
 * Note: This server handles CMS admin registration only.
 * The main primerforge Python backend handles all user-facing auth.
 *
 * Dependencies: bcryptjs (pure-JS, no native bindings required)
 *   npm install bcryptjs
 */

import express from 'express';
import bcrypt from 'bcryptjs';
import dotenv from 'dotenv';
import { BrevoClient } from '@getbrevo/brevo';

dotenv.config();

const app = express();
app.use(express.json({ limit: '1mb' }));

const PORT = process.env.PORT || 3001;
const BCRYPT_ROUNDS = 12; // OWASP recommended minimum cost factor

// NOTE: In-memory user store is for CMS admin only (small number of admins).
// For production scale, replace with a persistent database.
const users = [];

const brevo = new BrevoClient({ apiKey: process.env.BREVO_API_KEY });


/**
 * POST /api/register
 *
 * Register a new CMS admin user.
 * Passwords are hashed with bcrypt (cost=12) before storage.
 * Local-auth registrations require email verification before login.
 *
 * Body:
 *   { email: string, password?: string, auth_provider: 'local' | 'google' }
 *
 * Returns:
 *   201: { message: string, is_verified: boolean }
 *   400: { error: string }
 *   409: { error: 'Email already registered' }
 *   500: { error: 'Internal server error' }
 */
app.post('/api/register', async (req, res) => {
  try {
    const { email, password, auth_provider } = req.body;

    if (!email || !auth_provider) {
      return res.status(400).json({ error: 'email and auth_provider are required' });
    }

    // Basic email format check
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return res.status(400).json({ error: 'Invalid email format' });
    }

    if (auth_provider === 'local' && !password) {
      return res.status(400).json({ error: 'password is required for local registration' });
    }

    // Minimum password length check (full policy enforced on Python side)
    if (auth_provider === 'local' && password.length < 8) {
      return res.status(400).json({ error: 'Password must be at least 8 characters' });
    }

    if (users.find(u => u.email === email)) {
      return res.status(409).json({ error: 'Email already registered' });
    }

    if (auth_provider === 'google') {
      users.push({
        email,
        passwordHash: null,
        auth_provider: 'google',
        is_verified: true,
        verificationToken: null,
        tokenExpiry: null,
      });
      return res.status(201).json({ message: 'Registration successful', is_verified: true });
    }

    if (auth_provider === 'local') {
      // SEC-01 FIX: bcrypt with cost factor 12 (replaces insecure SHA-256)
      // bcrypt automatically generates a unique salt per password hash.
      const passwordHash = await bcrypt.hash(password, BCRYPT_ROUNDS);

      // Secure random verification token
      const { randomBytes } = await import('crypto');
      const verificationToken = randomBytes(32).toString('hex');
      const tokenExpiry = Date.now() + 60 * 60 * 1000; // 1 hour

      users.push({
        email,
        passwordHash,   // bcrypt hash — NOT raw password or SHA-256
        auth_provider: 'local',
        is_verified: false,
        verificationToken,
        tokenExpiry,
      });

      const baseUrl = process.env.APP_URL || 'http://localhost:8080';
      const activationUrl = `${baseUrl}/api/verify?token=${verificationToken}`;

      try {
        await brevo.transactionalEmails.sendTransacEmail({
          sender: {
            email: process.env.SMTP_FROM_EMAIL || 'noreply@vigyanllm.in',
            name: 'VigyanLLM',
          },
          to: [{ email }],
          subject: 'Activate your VigyanLLM account',
          htmlContent: `
            <p>Thank you for registering with VigyanLLM.</p>
            <p>Click the link below to activate your account:</p>
            <p><a href="${activationUrl}">${activationUrl}</a></p>
            <p>This link expires in 1 hour.</p>
            <p>If you did not create this account, please ignore this email.</p>
          `,
        });
      } catch (emailErr) {
        // Log but do not fail registration — token is still valid in memory
        console.error('Brevo send failed:', emailErr.message);
      }

      return res.status(201).json({
        message: 'Registration successful. Check your email to activate your account.',
      });
    }

    return res.status(400).json({
      error: 'Invalid auth_provider. Must be "google" or "local".',
    });
  } catch (err) {
    console.error('Register error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});


/**
 * GET /api/verify?token=<token>
 *
 * Verify a user's email address using the token from the activation email.
 * Redirects to /verified on success, returns 400 on invalid/expired token.
 */
app.get('/api/verify', (req, res) => {
  try {
    const { token } = req.query;

    if (!token) {
      return res.status(400).send('Invalid or expired token');
    }

    const user = users.find(u => u.verificationToken === token);

    if (!user || Date.now() > user.tokenExpiry) {
      return res.status(400).send('Invalid or expired token');
    }

    user.is_verified = true;
    user.verificationToken = null;
    user.tokenExpiry = null;

    const baseUrl = process.env.APP_URL || 'http://localhost:8080';
    res.redirect(`${baseUrl}/verified`);
  } catch (err) {
    console.error('Verify error:', err);
    res.status(500).send('Internal server error');
  }
});


app.listen(PORT, () => {
  console.log(`VigyanLLM CMS auth server running on port ${PORT}`);
});
