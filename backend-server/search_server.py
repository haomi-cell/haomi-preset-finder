#!/usr/bin/env python3
"""HAOMI Preset Finder backend v2 — /search + /resolve via Scrapling stealth."""
import json, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote, quote
import threading, time

# Cache TTL 15 menit — hindari scrape ulang untuk query yang sama (scrape = 30-60 detik)
_CACHE = {}
_CACHE_LOCK = threading.Lock()
CACHE_TTL = 900

def cache_get(key):
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL:
            return hit[1]
        if hit:
            del _CACHE[key]
    return None

def cache_set(key, value):
    with _CACHE_LOCK:
        _CACHE[key] = (time.time(), value)
        # jaga memori: max 200 entri, buang yang terlama
        if len(_CACHE) > 200:
            for k in sorted(_CACHE, key=lambda k: _CACHE[k][0])[:50]:
                del _CACHE[k]

def stealth_get(url):
    from scrapling.fetchers import StealthyFetcher
    return StealthyFetcher.fetch(url, headless=True, network_idle=True)

def tiktok_search(q):
    page = stealth_get('https://www.tiktok.com/search?q=' + quote(q, safe=''))
    html = page.html_content
    ids = list(dict.fromkeys(re.findall(r'/video/(\d{15,})', html)))[:12]
    return [{'id': v, 'url': f'https://www.tiktok.com/@i/video/{v}'} for v in ids]

def tiktok_resolve(vid_url):
    page = stealth_get(vid_url)
    html = page.html_content
    m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.S)
    if m:
        data = json.loads(m.group(1))
        item = data['__DEFAULT_SCOPE__']['webapp.video-detail']['itemInfo']['itemStruct']
    else:
        m = re.search(r'<script id="SIGI_STATE"[^>]*>(.*?)</script>', html, re.S)
        if not m: return None
        data = json.loads(m.group(1))
        modules = data.get('ItemModule', {})
        item = next(iter(modules.values())) if modules else None
    if not item: return None
    stats = item.get('stats', {})
    video = item.get('video', {})
    author = item.get('author', {})
    music = item.get('music', {})
    comments = item.get('comments', []) or []
    desc = item.get('desc', '')
    # link preset dari deskripsi + komentar
    texts = [desc] + [c.get('text', '') for c in comments[:40]]
    all_text = '\n'.join(texts)
    links = sorted(set(re.findall(r'https?://[^\s"\')<>]+', all_text)))
    links = [u for u in links if re.search(r'\.(xml|zip)', u, re.I) or re.search(r'preset|am_|alight|telegra|drive\.google|t\.me|s\.id|bit\.ly|cutt\.ly|lynk|saweria', u, re.I)]
    created = int(item.get('createTime') or 0)
    import datetime
    upload = datetime.datetime.fromtimestamp(created, datetime.timezone(datetime.timedelta(hours=7))).strftime('%Y-%m-%d %H:%M WIB') if created else 'unknown'
    return {
        'id': item.get('id'),
        'title': desc[:200],
        'cover': video.get('cover') or video.get('originCover') or '',
        'video': video.get('playAddr') or video.get('downloadAddr') or '',
        'stats': {
            'region': item.get('region') or item.get('locationCreated') or 'unknown',
            'resolusi': f"{video.get('width','?')}x{video.get('height','?')}",
            'durasi_detik': video.get('duration', 0),
            'upload_jam_lokal': upload,
            'like': stats.get('diggCount', 0),
            'komentar': stats.get('commentCount', 0),
            'share': stats.get('shareCount', 0),
            'views': stats.get('playCount', 0),
            'save': stats.get('collectCount', 0),
            'musik': music.get('title', 'unknown'),
            'author': {
                'username': author.get('uniqueId', 'unknown'),
                'nickname': author.get('nickname', 'unknown'),
                'followers': author.get('followerCount', 0),
                'avatar': author.get('avatarLarger', ''),
            },
        },
        'preset_links': links,
        'comments': [{'user': c.get('user', {}).get('uniqueId', '?'), 'text': c.get('text', '')[:120], 'likes': c.get('diggCount', 0)} for c in comments[:10]],
        'found': len(links) > 0,
    }


def tiktok_search_enriched(q, n=6):
    from concurrent.futures import ThreadPoolExecutor
    base = tiktok_search(q)
    def enrich(v):
        try:
            r = tiktok_resolve(v['url'])
            if r:
                v.update({
                    'author': r['stats']['author']['username'],
                    'title': r['title'],
                    'cover': r['cover'],
                    'duration': r['stats']['durasi_detik'],
                })
        except Exception:
            pass
        return v
    with ThreadPoolExecutor(max_workers=6) as ex:
        head = list(ex.map(enrich, base[:n]))
    return head + base[n:]



def tiktok_user(user, enrich=6):
    """Ambil video terbaru dari akun @user."""
    from concurrent.futures import ThreadPoolExecutor
    user = user.strip().lstrip('@')
    page = stealth_get(f'https://www.tiktok.com/@{user}')
    html = page.html_content
    ids = list(dict.fromkeys(re.findall(r'/video/(\d{15,})', html)))[:12]
    base = [{'id': i, 'url': f'https://www.tiktok.com/@{user}/video/{i}', 'author': user} for i in ids]
    def enrich_one(v):
        try:
            r = tiktok_resolve(v['url'])
            if r:
                v.update({'title': r['title'], 'cover': r['cover'], 'duration': r['stats']['durasi_detik']})
        except Exception: pass
        return v
    with ThreadPoolExecutor(max_workers=6) as ex:
        head = list(ex.map(enrich_one, base[:enrich]))
    return head + base[enrich:]

def media_proxy(url):
    import urllib.request
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) Chrome/120',
        'Referer': 'https://www.tiktok.com/',
    })
    return urllib.request.urlopen(req, timeout=30)


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'content-type')

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code); self._cors()
        self.send_header('content-type', 'application/json')
        self.send_header('content-length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


    def _media(self, url):
        if not url.startswith('http'): return self._json(400, {'error': 'url invalid'})
        try:
            resp = media_proxy(url)
            self.send_response(200); self._cors()
            self.send_header('content-type', resp.headers.get('Content-Type', 'video/mp4'))
            cl = resp.headers.get('Content-Length')
            if cl: self.send_header('content-length', cl)
            self.end_headers()
            while True:
                chunk = resp.read(65536)
                if not chunk: break
                self.wfile.write(chunk)
        except Exception as e:
            try: self._json(502, {'error': str(e)})
            except Exception: pass


    def do_POST(self):
        u = urlparse(self.path)
        try:
            length = int(self.headers.get('content-length') or 0)
            body = self.rfile.read(length) if length else b'{}'
            data = json.loads(body.decode() or '{}')
        except Exception:
            return self._json(400, {'error': 'body invalid'})
        # map POST /search {query}, /user {username}, /resolve {video} -> internal GET-style
        try:
            if u.path == '/search':
                q = str(data.get('query', ''))[:120]
                if not q: return self._json(400, {'error': 'query kosong'})
                ck = ('search', q.lower())
                res = cache_get(ck)
                if res is None:
                    res = tiktok_search_enriched(q)
                    cache_set(ck, res)
                return self._json(200, {'creator': '@xMSHaomi', 'status': True, 'result': res})
            if u.path == '/user':
                q = str(data.get('username', '')).lstrip('@')[:30]
                if not q: return self._json(400, {'error': 'username kosong'})
                ck = ('user', q.lower())
                vids = cache_get(ck)
                if vids is None:
                    vids = tiktok_user(q)
                    if vids is None: return self._json(502, {'error': 'Akun tidak ditemukan'})
                    cache_set(ck, vids)
                return self._json(200, {'creator': '@xMSHaomi', 'status': True, 'result': vids})
            if u.path == '/resolve':
                q = str(data.get('video', ''))
                if not q: return self._json(400, {'error': 'url kosong'})
                r = tiktok_resolve(q)
                if not r: return self._json(502, {'error': 'Gagal ekstrak data video'})
                return self._json(200, {'creator': '@xMSHaomi', 'status': True, 'result': r})
            return self._json(404, {'error': 'not found'})
        except Exception as e:
            return self._json(500, {'error': str(e)})

    def do_GET(self):
        u = urlparse(self.path)
        q = unquote(parse_qs(u.query).get('q', [''])[0])[:120]
        try:
            if u.path == '/xml':
                if not q.startswith('http'): return self._json(400, {'error': 'url invalid'})
                import urllib.request
                try:
                    req = urllib.request.Request(q, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        raw = resp.read(5 * 1024 * 1024 + 1)
                        if len(raw) > 5 * 1024 * 1024:
                            return self._json(413, {'error': 'XML lebih dari 5 MB'})
                        text = raw.decode('utf-8', 'replace')
                    if '<scene' not in text[:3000] and '<shape' not in text[:3000]:
                        return self._json(400, {'error': 'Bukan XML preset'})
                    self.send_response(200); self._cors()
                    self.send_header('content-type', 'text/xml; charset=utf-8')
                    self.send_header('content-length', str(len(text)))
                    self.end_headers()
                    self.wfile.write(text[:2_000_000].encode())
                except Exception as e:
                    self._json(502, {'error': str(e)})
                return
            if u.path == '/media':
                return self._media(q)
            if u.path == '/health':
                return self._json(200, {'status': True, 'creator': '@xMSHaomi'})
            if u.path == '/search':
                if not q: return self._json(400, {'error': 'q kosong'})
                ck = ('search', q.lower())
                res = cache_get(ck)
                if res is None:
                    res = tiktok_search_enriched(q)
                    cache_set(ck, res)
                return self._json(200, {'creator': '@xMSHaomi', 'status': True, 'result': res})
            if u.path == '/resolve':
                if not q: return self._json(400, {'error': 'url kosong'})
                ck = ('resolve', q)
                r = cache_get(ck)
                if r is None:
                    r = tiktok_resolve(q)
                    if r: cache_set(ck, r)
                if not r: return self._json(502, {'error': 'Gagal ekstrak data video'})
                return self._json(200, {'creator': '@xMSHaomi', 'status': True, 'result': r})
            if u.path == '/user':
                if not q: return self._json(400, {'error': 'username kosong'})
                ck = ('user', q.lower())
                vids = cache_get(ck)
                if vids is None:
                    vids = tiktok_user(q)
                    if vids is None: return self._json(502, {'error': 'Akun tidak ditemukan'})
                    cache_set(ck, vids)
                return self._json(200, {'creator': '@xMSHaomi', 'status': True, 'result': vids})
            self._json(404, {'error': 'not found'})
        except Exception as e:
            self._json(500, {'error': str(e)})

    def log_message(self, *a): pass

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', int(__import__('os').environ.get('PORT', '8901'))), Handler).serve_forever()
