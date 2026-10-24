// HAOMI Preset Finder — user endpoint: cari video dari akun @username (via backend stealth)
const BACKENDS = ['https://ferry-ticket-vehicle-handy.trycloudflare.com'];

async function tryBackends(path) {
  for (const b of BACKENDS) {
    try {
      const r = await fetch(b + path, { signal: AbortSignal.timeout(90000) });
      if (r.ok) return await r.json();
    } catch (e) {}
  }
  return null;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'content-type');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { username } = req.body || {};
  const u = String(username || '').trim().replace(/^@/, '').slice(0, 30);
  if (!/^[A-Za-z0-9._]{2,30}$/.test(u)) return res.status(400).json({ error: 'Username tidak valid' });

  const j = await tryBackends('/user?q=' + encodeURIComponent(u));
  if (!j || !j.status) return res.status(502).json({ error: j?.error || 'Akun tidak ditemukan / backend down' });
  return res.status(200).json(j);
}
