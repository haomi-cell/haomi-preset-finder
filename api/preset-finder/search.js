// HAOMI Preset Finder — search via backend server (Scrapling stealth) + enrich metadata via tikwm/oEmbed
const BACKENDS = [
  'https://ferry-ticket-vehicle-handy.trycloudflare.com',
];

async function tryBackends(path) {
  for (const b of BACKENDS) {
    try {
      const r = await fetch(b + path, { signal: AbortSignal.timeout(60000) });
      if (r.ok) return await r.json();
    } catch (e) { /* next */ }
  }
  return null;
}

// enrich single video via TikTok oEmbed (public, reliable)
async function oembed(url) {
  try {
    const r = await fetch('https://www.tiktok.com/oembed?url=' + encodeURIComponent(url), {
      signal: AbortSignal.timeout(10000),
    });
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'content-type');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { query } = req.body || {};
  const q = String(query || '').trim().slice(0, 120);
  if (!q) return res.status(400).json({ error: 'Query kosong' });

  const j = await tryBackends('/search?q=' + encodeURIComponent(q));
  if (!j || !j.status) return res.status(502).json({ error: 'Backend pencarian tidak tersedia, coba lagi nanti' });

  // enrich concurrency 4
  const vids = j.result.slice(0, 12);
  const enriched = await Promise.all(vids.map(async v => {
    const o = await oembed(v.url);
    return {
      ...v,
      author: o?.author_unique_id || o?.author_name || v.author,
      title: o?.title || v.title,
      cover: o?.thumbnail_url || v.cover,
    };
  }));

  return res.status(200).json({ creator: '@xMSHaomi', status: true, result: enriched });
}
