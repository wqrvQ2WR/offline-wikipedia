#!/usr/bin/env python3
"""오프라인 위키디피아 관리 앱.

페이지 추가/삭제/갱신을 브라우저에서 할 수 있는 로컬 웹 서버.
실행: python3 app.py [--open]   (--open이면 브라우저 자동 열기)
"""
import json
import mimetypes
import shutil
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
import update as wiki  # noqa: E402  (같은 폴더의 update.py 재사용)

PORT = 8459


def page_filename(lang, title):
    return "{} ({}).html".format(title.replace("/", "_"), lang)


def list_pages():
    out = []
    for lang, title in wiki.load_pages():
        f = BASE_DIR / page_filename(lang, title)
        info = {"lang": lang, "title": title, "file": f.name, "exists": f.exists()}
        if f.exists():
            st = f.stat()
            info["size"] = st.st_size
            info["updated"] = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
        out.append(info)
    return out


def download_one(lang, title):
    html = wiki.fetch_page(lang, title)
    return wiki.save_page(lang, title, html)


def add_page(lang, title):
    if (lang, title) in wiki.load_pages():
        return {"ok": False, "error": "이미 목록에 있는 문서예요."}
    out = download_one(lang, title)  # 받아지는 문서인지 먼저 확인
    with (BASE_DIR / "pages.txt").open("a", encoding="utf-8") as f:
        f.write("{}:{}\n".format(lang, title))
    return {"ok": True, "file": out.name}


def remove_page(lang, title):
    pages_file = BASE_DIR / "pages.txt"
    kept = []
    for line in pages_file.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and ":" in s:
            l, t = s.split(":", 1)
            if l.strip() == lang and t.strip() == title:
                continue
        kept.append(line)
    pages_file.write_text("\n".join(kept) + "\n", encoding="utf-8")
    f = BASE_DIR / page_filename(lang, title)
    if f.exists():
        f.unlink()
    photos = BASE_DIR / "{} 사진".format(title.replace("/", "_"))
    if photos.is_dir():
        shutil.rmtree(photos)
    return {"ok": True}


def update_all():
    results = []
    for lang, title in wiki.load_pages():
        try:
            out = download_one(lang, title)
            results.append({"lang": lang, "title": title, "ok": True,
                            "size": out.stat().st_size})
        except Exception as e:
            results.append({"lang": lang, "title": title, "ok": False, "error": str(e)})
    ok = sum(1 for r in results if r["ok"])
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with (BASE_DIR / "update.log").open("a", encoding="utf-8") as f:
        f.write("[{}] (앱에서 수동 갱신) 성공 {}건, 실패 {}건\n".format(
            stamp, ok, len(results) - ok))
    return {"ok": True, "results": results}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, content_type):
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def do_GET(self):
        path = unquote(self.path.split("?", 1)[0])
        if path == "/":
            return self._file(BASE_DIR / "index.html", "text/html; charset=utf-8")
        if path == "/api/pages":
            return self._json({"pages": list_pages()})
        if path.startswith("/files/"):
            name = path[len("/files/"):]
            target = (BASE_DIR / name).resolve()
            # 사진 폴더 등 하위 경로도 서빙 (BASE_DIR 밖 접근 차단)
            if target.is_file() and str(target).startswith(str(BASE_DIR) + "/"):
                if target.suffix == ".html":
                    return self._file(target, "text/html; charset=utf-8")
                ctype = mimetypes.guess_type(target.name)[0]
                if ctype and ctype.startswith("image/"):
                    return self._file(target, ctype)
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = unquote(self.path)
        try:
            data = self._body()
            if path == "/api/add":
                return self._json(add_page(data["lang"].strip(), data["title"].strip()))
            if path == "/api/remove":
                return self._json(remove_page(data["lang"], data["title"]))
            if path == "/api/update":
                return self._json(update_all())
        except Exception as e:
            return self._json({"ok": False, "error": str(e)}, 500)
        self._json({"error": "not found"}, 404)


def main():
    url = "http://localhost:{}".format(PORT)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError as e:
        if e.errno == 48:  # 이미 실행 중이면 브라우저만 열어준다
            print("앱이 이미 켜져 있어요 → {}".format(url))
            webbrowser.open(url)
            return
        raise
    print("오프라인 위키디피아 관리 앱: {}".format(url))
    if "--open" in sys.argv:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
