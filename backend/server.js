import express from 'express';
import crypto from 'crypto';
import dotenv from 'dotenv';
import { BrevoClient } from '@getbrevo/brevo';

dotenv.config();

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3001;

const users = [];

const brevo = new BrevoClient({ apiKey: process.env.BREVO_API_KEY });

app.post('/api/register', async (req, res) => {
  try {
    const { email, password, auth_provider } = req.body;

    if (!email || !auth_provider) {
      return res.status(400).json({ error: 'email and auth_provider are required' });
    }

    if (auth_provider === 'local' && !password) {
      return res.status(400).json({ error: 'password is required for local registration' });
    }

    if (users.find(u => u.email === email)) {
      return res.status(409).json({ error: 'Email already registered' });
    }

    if (auth_provider === 'google') {
      users.push({
        email,
        password: null,
        auth_provider: 'google',
        is_verified: true,
        verificationToken: null,
        tokenExpiry: null,
      });
      return res.json({ message: 'Registration successful', is_verified: true });
    }

    if (auth_provider === 'local') {
      const passwordHash = crypto.createHash('sha256').update(password).digest('hex');
      const verificationToken = crypto.randomBytes(32).toString('hex');
      const tokenExpiry = Date.now() + 60 * 60 * 1000;

      users.push({
        email,
        password: passwordHash,
        auth_provider: 'local',
        is_verified: false,
        verificationToken,
        tokenExpiry,
      });

      const baseUrl = process.env.APP_URL || 'http://localhost:8080';
      const activationUrl = `${baseUrl}/api/verify?token=${verificationToken}`;

      try {
        await brevo.transactionalEmails.sendTransacEmail({
          sender: { email: process.env.SMTP_FROM_EMAIL || 'noreply@vigyanllm.in', name: 'VigyanLLM' },
          to: [{ email }],
          subject: 'Activate your account',
          htmlContent: `<p>Thank you for registering.</p><p>Click the link below to activate your account:</p><p><a href="${activationUrl}">${activationUrl}</a></p><p>This link expires in 1 hour.</p>`,
        });
      } catch (emailErr) {
        console.error('Brevo send failed:', emailErr.message);
      }

      return res.json({ message: 'Registration successful. Check your email to activate your account.' });
    }

    return res.status(400).json({ error: 'Invalid auth_provider. Must be "google" or "local".' });
  } catch (err) {
    console.error('Register error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

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
  console.log(`Auth server running on port ${PORT}`);
});
