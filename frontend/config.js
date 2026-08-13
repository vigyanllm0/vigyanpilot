// ── VigyanLLM Backend Config ──────────────────────────────────────────────
// For Vercel production, uses proxy rewrite (/api/* -> ngrok tunnel).
// For local dev, this file sets the ngrok URL directly.
// .gitignore keeps this file out of git.

window.VIGYAN_BACKEND_URL = '/api';
