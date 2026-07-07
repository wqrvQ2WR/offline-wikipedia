#!/usr/bin/env python3
"""오프라인 위키백과 갱신 스크립트.

pages.txt에 적힌 문서들을 위키백과에서 받아와 HTML로 저장한다.
이미 있는 파일은 덮어쓴다 (what-if.xkcd.com/59 의 '인쇄본 최신화'를 프린터 없이).
"""
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


def save_page(lang, title, html):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if lang == "namu":
        site, base = "namu.wiki", "https://namu.wiki/"
        # SPA 스크립트가 오프라인 사본을 다시 그리려다 깨지지 않게 제거 (SSR 본문만 남김)
        html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    else:
        site = "{}.wikipedia.org".format(lang)
        base = "https://{}.wikipedia.org/wiki/".format(lang)
    banner = ('<div class="updated-banner">📄 오프라인 사본 — {} 기준 '
              '({} / {})</div>'.format(now, site, title))
    # 상대 경로 리소스(이미지 등)가 온라인일 때 보이도록 base 지정
    head_extra = '<base href="{}">{}'.format(base, STYLE)
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
