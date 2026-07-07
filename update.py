#!/usr/bin/env python3
"""오프라인 위키백과 갱신 스크립트.

pages.txt에 적힌 문서들을 위키백과에서 받아와 HTML로 저장한다.
이미 있는 파일은 덮어쓴다 (what-if.xkcd.com/59 의 '인쇄본 최신화'를 프린터 없이).
"""
import hashlib
import re
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PAGES_FILE = BASE_DIR / "pages.txt"
LOG_FILE = BASE_DIR / "update.log"
USER_AGENT = "OfflineWikipediaDaily/1.0 (personal offline copy; claudecode6672@gmail.com)"
# 나무위키는 스크립트 UA를 차단하므로 브라우저 UA 사용
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

STYLE = """<style>
body { max-width: 860px; margin: 2em auto; padding: 0 1em;
       font-family: -apple-system, "Apple SD Gothic Neo", sans-serif; line-height: 1.6; }
img { max-width: 100%; height: auto; }
table { border-collapse: collapse; } td, th { border: 1px solid #ccc; padding: 4px 8px; }
.updated-banner { background: #f8f9fa; border: 1px solid #a2a9b1; padding: 8px 12px;
                  font-size: 0.85em; color: #54595d; margin-bottom: 1.5em; }
</style>"""


def load_pages():
    pages = []
    for line in PAGES_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        lang, title = line.split(":", 1)
        pages.append((lang.strip(), title.strip()))
    return pages


def fetch_page(lang, title, retries=2):
    if lang == "namu":
        url = "https://namu.wiki/w/" + urllib.parse.quote(title, safe="")
        ua = BROWSER_UA
    else:
        url = "https://{}.wikipedia.org/api/rest_v1/page/html/{}".format(
            lang, urllib.parse.quote(title.replace(" ", "_"), safe=""))
        ua = USER_AGENT
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            if attempt == retries:
                raise
            time.sleep(3)


def inline_stylesheets(html, base_url):
    """<link rel=stylesheet>를 CSS 본문을 담은 <style>로 교체해 오프라인에서도 스타일 유지."""
    def fix_css_urls(css, css_url):
        # CSS 안의 상대 경로(폰트 등)를 절대 URL로 — base 태그 없이도 온라인이면 로드되게
        def u(m):
            q, val = m.group(1), m.group(2)
            if val.startswith(("data:", "http://", "https://", "#")):
                return m.group(0)
            return "url({}{}{})".format(q, urllib.parse.urljoin(css_url, val), q)
        return re.sub(r'url\(\s*(["\']?)([^"\')\s]+)\1\s*\)', u, css)

    def repl(m):
        tag = m.group(0)
        href = re.search(r'href=["\']([^"\']+)', tag)
        if not href:
            return tag
        url = urllib.parse.urljoin(base_url, href.group(1))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                css = resp.read().decode("utf-8", "replace")
            return "<style>{}</style>".format(fix_css_urls(css, url))
        except Exception:
            return tag  # 실패하면 원래 링크 유지 (온라인에선 여전히 동작)
    return re.sub(r'<link\b[^>]*rel=["\']stylesheet["\'][^>]*>', repl, html)


def absolutify(html, page_base):
    """href/src 상대 경로를 절대 URL로 바꿔 base 태그 없이도 링크가 살게 한다."""
    def repl(m):
        attr, q, val = m.group(1), m.group(2), m.group(3)
        if val.startswith(("#", "data:", "http://", "https://", "mailto:", "javascript:")):
            return m.group(0)
        return "{}={}{}{}".format(attr, q, urllib.parse.urljoin(page_base, val), q)
    return re.sub(r'\b(href|src|poster)=(["\'])([^"\']*)\2', repl, html)


def localize_images(html, page_base, title):
    """이미지를 '<제목> 사진' 폴더에 내려받고 사본이 로컬 파일을 가리키게 한다."""
    folder = "{} 사진".format(title.replace("/", "_"))
    img_dir = BASE_DIR / folder
    seen = {}

    def download(url):
        if url in seen:
            return seen[url]
        ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif"):
            ext = ".img"
        name = hashlib.sha1(url.encode()).hexdigest()[:16] + ext
        target = img_dir / name
        if not target.exists():  # 같은 이미지는 다음 갱신 때 다시 받지 않음
            req = urllib.request.Request(url, headers={
                "User-Agent": BROWSER_UA, "Referer": page_base})
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        img_dir.mkdir(exist_ok=True)
                        target.write_bytes(resp.read())
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(2)
        local = "{}/{}".format(urllib.parse.quote(folder), urllib.parse.quote(name))
        seen[url] = local
        return local

    def repl(m):
        tag = m.group(0)
        # lazy-loading(나무위키)은 진짜 주소가 data-src에 있음
        src = re.search(r'\bdata-src=(["\'])([^"\']+)\1', tag) or \
              re.search(r'\bsrc=(["\'])([^"\']+)\1', tag)
        if not src:
            return tag
        url = urllib.parse.urljoin(page_base, src.group(2))
        if url.startswith("data:"):
            return tag
        try:
            local = download(url)
        except Exception:
            local = url  # 실패하면 온라인 주소라도 남김
        tag = re.sub(r'\s+(srcset|data-src|data-srcset|loading)=(["\'])[^"\']*\2', "", tag)
        return re.sub(r'\bsrc=(["\'])[^"\']*\1', 'src="{}"'.format(local), tag)

    return re.sub(r"<img\b[^>]*>", repl, html)


def save_page(lang, title, html):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if lang == "namu":
        site, base = "namu.wiki", "https://namu.wiki/"
        # SPA 스크립트가 오프라인 사본을 다시 그리려다 깨지지 않게 제거 (SSR 본문만 남김)
        html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
        extra_css = ""  # 나무위키 자체 스타일과 충돌하지 않게 우리 스타일은 생략
    else:
        site = "{}.wikipedia.org".format(lang)
        base = "https://{}.wikipedia.org/wiki/".format(lang)
        extra_css = STYLE
    # 기존/삽입 base 태그 없이 동작하게: 링크는 절대 URL로, 이미지는 로컬 폴더로
    html = re.sub(r"<base\b[^>]*>", "", html)
    html = absolutify(html, base)
    if lang == "namu":
        # 난독화 클래스 기반 CSS를 통째로 심어야 오프라인에서 제대로 보임
        html = inline_stylesheets(html, base)
    html = localize_images(html, base, title)
    banner = ('<div style="background:#f8f9fa;border:1px solid #a2a9b1;padding:8px 12px;'
              'font-size:.85em;color:#54595d;margin-bottom:1.5em;">📄 오프라인 사본 — {} 기준 '
              '({} / {})</div>'.format(now, site, title))
    head_extra = extra_css
    html = re.sub(r"<head([^>]*)>", r"<head\1>" + head_extra.replace("\\", "\\\\"), html, count=1)
    html = re.sub(r"<body([^>]*)>", r"<body\1>" + banner.replace("\\", "\\\\"), html, count=1)
    safe_name = title.replace("/", "_")
    out = BASE_DIR / "{} ({}).html".format(safe_name, lang)
    out.write_text(html, encoding="utf-8")
    return out


def main():
    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ok, failed = [], []
    for lang, title in load_pages():
        try:
            html = fetch_page(lang, title)
            out = save_page(lang, title, html)
            ok.append("{}:{} → {} ({:,} bytes)".format(lang, title, out.name, out.stat().st_size))
        except Exception as e:
            failed.append("{}:{} → {}".format(lang, title, e))
    lines = ["[{}] 성공 {}건, 실패 {}건".format(started, len(ok), len(failed))]
    lines += ["  OK  " + s for s in ok] + ["  FAIL " + s for s in failed]
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(1 if failed and not ok else 0)


if __name__ == "__main__":
    main()
