import os, re, json, time, urllib.request, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

PORT = int(os.environ.get("PORT", 8080))
PROXIES = ["http://36.155.23.163:10808", ""]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

def xor_decrypt(ch_hex, kh_hex):
    try:
        c, k = bytes.fromhex(ch_hex), bytes.fromhex(kh_hex)
        return bytes([b ^ k[i % len(k)] for i, b in enumerate(c)]).decode("utf-8", errors="ignore")
    except Exception: return None

def fetch_url(url, referer, proxy=""):
    req = urllib.request.Request(url, headers={**HEADERS, "Referer": referer, "Origin": referer.rstrip("/")})
    handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy})] if proxy else []
    with urllib.request.build_opener(*handlers).open(req, timeout=8) as r:
        return r.read().decode("utf-8", errors="ignore")

def resolve_videocdn_manifest(channel_id):
    for proxy in PROXIES:
        for var in ["shopping4", "shopping2", "shopping", "mz"]:
            try:
                html = fetch_url(f"https://videocdn-4727.website/{var}/?channel_id={channel_id}", "https://strumyk.cv/", proxy)
                if not html or "offline" in html.lower(): continue
                m_c, m_k = re.search(r'vars+_cs*=s*"([0-9a-fA-F]+)"', html), re.search(r'vars+_ks*=s*"([0-9a-fA-F]+)"', html)
                real_m3u8 = xor_decrypt(m_c.group(1), m_k.group(1)) if (m_c and m_k) else None
                if not real_m3u8:
                    m = re.search(r'["'](https?://[^"']+.m3u8[^"']*)["']', html)
                    real_m3u8 = m.group(1) if m else None
                if real_m3u8 and real_m3u8.startswith("http"):
                    m3u = fetch_url(real_m3u8, "https://videocdn-4727.website/", proxy)
                    if m3u and "#EXTM3U" in m3u:
                        return {"success": True, "channel_id": channel_id, "manifest": m3u}
            except Exception: continue
    return {"success": False, "error": "Offline"}

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer): daemon_threads = True

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if parsed.path in ["", "/", "/health"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
        m_man = re.match(r"^/manifest(?:/([^/]+?)(?:.m3u8)?)?$", parsed.path.rstrip("/"))
        ch_id = (m_man.group(1) if m_man and m_man.group(1) else None) or qs.get("id", [None])[0]
        if not ch_id:
            self.send_error(400, "Missing id")
            return
        res = resolve_videocdn_manifest(ch_id)
        if not res.get("success"):
            self.send_error(502, "Error")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.apple.mpegurl; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(res["manifest"].encode("utf-8"))
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
