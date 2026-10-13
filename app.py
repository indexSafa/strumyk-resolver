import os
from flask import Flask, Response, request
import requests

app = Flask(__name__)

@app.route('/')
def index():
    return "Strumyk Resolver Worker / Proxy active!"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/proxy')
def proxy():
    url = request.args.get('url')
    if not url:
        return "Missing url", 400
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, stream=True, timeout=10)
        return Response(r.iter_content(chunk_size=1024), content_type=r.headers.get('content-type'))
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
