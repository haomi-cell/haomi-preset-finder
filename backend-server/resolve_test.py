
import json, re
from scrapling.fetchers import StealthyFetcher

def resolve_video(vid_url):
    page = StealthyFetcher.fetch(vid_url, headless=True, network_idle=True)
    html = page.html_content
    m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        m = re.search(r'<script id="SIGI_STATE"[^>]*>(.*?)</script>', html, re.S)
        if not m: return None
        data = json.loads(m.group(1))
        modules = data.get('ItemModule', {})
        item = next(iter(modules.values())) if modules else {}
    else:
        data = json.loads(m.group(1))
        item = data['__DEFAULT_SCOPE__']['webapp.video-detail']['itemInfo']['itemStruct']
    stats = item.get('stats', {})
    video = item.get('video', {})
    author = item.get('author', {})
    music = item.get('music', {})
    comments = item.get('comments', []) or []
    desc = item.get('desc', '')
    clinks = []
    for c in comments[:40]:
        t = c.get('text','')
        clinks += (re.findall(r'https?://\S+', t)) if False else []
    return {
        'id': item.get('id'),
        'desc': desc,
        'cover': video.get('cover') or video.get('originCover'),
        'play': video.get('playAddr') or video.get('downloadAddr'),
        'region': item.get('region'),
        'w': video.get('width'), 'h': video.get('height'),
        'duration': video.get('duration'),
        'createTime': item.get('createTime'),
        'digg': stats.get('diggCount'), 'comment': stats.get('commentCount'),
        'share': stats.get('shareCount'), 'play': stats.get('playCount'),
        'collect': stats.get('collectCount'),
        'author': {'username': author.get('uniqueId'), 'nickname': author.get('nickname'), 'followers': author.get('followerCount'), 'avatar': author.get('avatarLarger')},
        'music': music.get('title'),
        'comments_raw': [c.get('text','')[:150] for c in comments[:30]],
    }

if __name__ == '__main__':
    r = resolve_video('https://www.tiktok.com/@i/video/7697858661338598677')
    print(json.dumps(r, indent=1)[:1200] if r else 'FAILED')
