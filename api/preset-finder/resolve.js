
export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'content-type');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { video } = req.body || {};
  const v = String(video || '').trim();
  if (!/tiktok\.com/.test(v)) return res.status(400).json({ error: 'URL TikTok tidak valid' });
  const idMatch = v.match(/(\d{6,})/);
  if (!idMatch) return res.status(400).json({ error: 'ID video tidak ditemukan' });
  const id = idMatch[1];
  const UA = { 'user-agent': 'Mozilla/5.0 (Linux; Android 13) Chrome/120 Mobile' };
  const fmt = n => Number(n) || 0;

  let info = {};
  // source 1: tikwm
  try {
    const r = await fetch(`https://tikwm.com/api/?url=${encodeURIComponent(v)}`, { headers: UA, signal: AbortSignal.timeout(12000) });
    const j = await r.json().catch(() => ({}));
    info = j?.data || {};
  } catch (e) {}
  // source 2 fallback: oEmbed (limited stats)
  let o = null;
  if (!info.title) {
    try {
      const r = await fetch('https://www.tiktok.com/oembed?url=' + encodeURIComponent(v), { signal: AbortSignal.timeout(10000) });
      if (r.ok) o = await r.json();
    } catch (e) {}
  }
  const desc = String(info.title || o?.title || '');

  // komentar via tikwm
  let commentLinks = [], topComments = [];
  try {
    const rc = await fetch(`https://tikwm.com/api/comment/list/?aweme_id=${id}&count=30&cursor=0`, { headers: UA, signal: AbortSignal.timeout(12000) });
    const jc = await rc.json().catch(() => ({}));
    for (const c of (jc?.data?.comments || [])) {
      const text = String(c.text || '');
      commentLinks.push(...(text.match(/https?:\/\/[^\s]+/g) || []));
      topComments.push({ user: c.user?.unique_id || c.user?.nickname || '?', text: text.slice(0, 120), likes: fmt(c.digg_count) });
    }
  } catch (e) {}

  const allText = desc + '\n' + topComments.map(c => c.text).join('\n') + '\n' + commentLinks.join('\n');
  const links = [...new Set((allText.match(/https?:\/\/[^\s"')]+/g) || []).filter(u =>
    /\.(xml|zip)/i.test(u) || /preset|am_|alight|telegra|drive\.google|t\.me|s\.id|bit\.ly|cutt\.ly/i.test(u)))];

  const created = fmt(info.create_time);
  return res.status(200).json({
    creator: '@xMSHaomi', status: true,
    result: {
      id,
      url: v,
      title: desc.slice(0, 200),
      cover: info.cover || o?.thumbnail_url || '',
      video: info.play || '',
      stats: {
        region: info.region || 'unknown',
        resolusi: info.width && info.height ? `${info.width}x${info.height}` : 'unknown',
        durasi_detik: fmt(info.duration),
        upload_jam_lokal: created ? new Date(created * 1000).toLocaleString('id-ID', { timeZone: 'Asia/Jakarta' }) : (o ? 'n/a (oembed)' : 'unknown'),
        like: fmt(info.digg_count),
        komentar: fmt(info.comment_count),
        share: fmt(info.share_count),
        views: fmt(info.play_count),
        download: fmt(info.download_count),
        save: fmt(info.collect_count),
        musik: info.music_info?.title || (o?.title ? '' : 'unknown'),
        author: {
          username: info.author?.unique_id || o?.author_unique_id || 'unknown',
          nickname: info.author?.nickname || o?.author_name || 'unknown',
          followers: fmt(info.author?.followers),
          avatar: info.author?.avatar || '',
        },
      },
      preset_links: links,
      comments: topComments.slice(0, 10),
      found: links.length > 0,
    },
  });
}
