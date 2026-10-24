// HAOMI Preset Finder — render proxy: ambil XML preset dari link eksternal (CORS-free)
export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const { url } = req.query;
  if (!url || !/^https?:\/\//i.test(url)) return res.status(400).json({ error: 'URL tidak valid' });
  // hanya izinkan tipe xml/text
  try {
    const parsed = new URL(url);
    if (!['http:', 'https:'].includes(parsed.protocol) || !parsed.hostname) return res.status(400).json({ error: 'URL tidak valid' });
    const r = await fetch(parsed.href, { signal: AbortSignal.timeout(15000), redirect: 'follow' });
    if (!r.ok) return res.status(502).json({ error: 'Upstream ' + r.status });
    const declaredSize = Number(r.headers.get('content-length') || 0);
    if (declaredSize > 5 * 1024 * 1024) return res.status(413).json({ error: 'File XML lebih dari 5 MB' });
    const text = await r.text();
    if (Buffer.byteLength(text, 'utf8') > 5 * 1024 * 1024) return res.status(413).json({ error: 'File XML lebih dari 5 MB' });
    if (!/<scene|<shape|xml/i.test(text.slice(0, 2000))) return res.status(400).json({ error: 'Bukan file XML preset' });
    res.setHeader('content-type', 'text/xml; charset=utf-8');
    return res.status(200).send(text.slice(0, 2_000_000));
  } catch (e) {
    return res.status(502).json({ error: 'Gagal ambil: ' + e.message });
  }
}
