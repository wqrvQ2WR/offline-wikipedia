# 📚 오프라인 위키디피아 / Offline Wikipedia

**한국어** | [English](#-offline-wikipedia-english)

> xkcd [what-if #59 "Updating a Printed Wikipedia"](https://what-if.xkcd.com/59/)에서 시작한 프로젝트.
> 랜들 먼로 계산으로는 인쇄본 위키피디아를 최신으로 유지하는 데 프린터 6대와 월 50만 달러(대부분 잉크값)가 필요하다.
> 이 저장소는 같은 일을 프린터 0대, 잉크값 $0로 한다.

원하는 위키백과·나무위키 문서들을 오프라인 HTML 사본으로 저장하고, 매일 한 번 자동으로 최신 내용으로 덮어쓴다.

## 구성

| 파일 | 역할 |
|---|---|
| `update.py` | `pages.txt`의 문서들을 위키백과 REST API로 받아 HTML로 저장 (의존성 없음, Python 3 내장 모듈만) |
| `pages.txt` | 받아올 문서 목록 — `언어코드:문서제목` 형식, 한 줄에 하나 |
| `app.py` + `index.html` | 관리 웹앱 (포트 8459) — 검색해서 추가, 삭제, 전체 갱신, 사본 열기 |
| `위키 관리 앱 실행.command` | 더블클릭으로 앱 실행 (macOS) |

## 사용법

```bash
# 한 번 갱신
python3 update.py

# 관리 앱 실행 → http://localhost:8459
python3 app.py --open
```

문서 추가는 앱에서 검색하거나, `pages.txt`에 `ko:문서제목` 한 줄 추가하면 된다.

### 지원 사이트

| 코드 | 사이트 | 비고 |
|---|---|---|
| `ko`, `en` 등 | 위키백과 (해당 언어판) | 검색 자동완성 지원 |
| `namu` | 나무위키 | 검색 API가 없어 **정확한 문서 제목**을 입력해야 함. 오프라인 사본은 스크립트를 제거한 정적 스냅샷으로 저장 |

## 매일 자동 갱신 (macOS launchd)

`~/Library/LaunchAgents/com.<이름>.offline-wikipedia.plist`를 만들어 `update.py`를 매일 실행하게 등록한다:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.example.offline-wikipedia</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/절대/경로/update.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
</dict>
</plist>
```

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.offline-wikipedia.plist
```

⚠️ **주의**: 프로젝트 폴더를 `~/Desktop`, `~/Documents`, `~/Downloads` 아래에 두면 macOS 보안(TCC) 때문에 launchd 자동 실행이 `Operation not permitted`로 실패한다. `~/Library/OfflineWikipedia` 같은 보호 구역 밖 경로에 두고, 필요하면 원하는 위치에 심볼릭 링크를 만들자.

## 한계

- 본문 텍스트와 표는 완전 오프라인으로 읽을 수 있지만, 이미지는 위키백과 서버에서 불러오므로 온라인일 때만 보인다.
- 위키피디아가 블랙아웃 항의를 하면 매직펜으로 직접 칠해야 한다.

---

# 📚 Offline Wikipedia (English)

[한국어](#-오프라인-위키디피아--offline-wikipedia) | **English**

> A project inspired by xkcd's [what-if #59 "Updating a Printed Wikipedia"](https://what-if.xkcd.com/59/).
> By Randall Munroe's math, keeping a printed Wikipedia up to date takes 6 printers and about $500,000 a month (mostly ink).
> This repo does the same job with 0 printers and $0 of ink.

It saves the Wikipedia and Namuwiki articles you choose as offline HTML copies, and overwrites them with the latest content once a day.

## What's inside

| File | Role |
|---|---|
| `update.py` | Downloads the articles listed in `pages.txt` via the Wikipedia REST API and saves them as HTML (no dependencies, Python 3 stdlib only) |
| `pages.txt` | List of articles to fetch — one per line, in `langcode:Article title` format |
| `app.py` + `index.html` | Management web app (port 8459) — search & add, remove, refresh all, open saved copies |
| `위키 관리 앱 실행.command` | Double-click launcher for the app (macOS) |

## Usage

```bash
# Refresh once
python3 update.py

# Run the management app → http://localhost:8459
python3 app.py --open
```

To add an article, search for it in the app, or append a line like `en:Moon` to `pages.txt`.

### Supported sites

| Code | Site | Notes |
|---|---|---|
| `ko`, `en`, etc. | Wikipedia (that language edition) | Search autocomplete supported |
| `namu` | Namuwiki (namu.wiki, Korean wiki) | No search API — enter the **exact article title**. Offline copies are saved as static snapshots with scripts stripped |

## Daily auto-update (macOS launchd)

Create `~/Library/LaunchAgents/com.<name>.offline-wikipedia.plist` to run `update.py` daily:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.example.offline-wikipedia</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/absolute/path/to/update.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
</dict>
</plist>
```

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.offline-wikipedia.plist
```

⚠️ **Warning**: If the project folder lives under `~/Desktop`, `~/Documents`, or `~/Downloads`, macOS privacy protection (TCC) blocks launchd from running it — you'll get `Operation not permitted`. Keep it outside protected areas (e.g. `~/Library/OfflineWikipedia`) and drop a symlink wherever you like.

## Limitations

- Article text and tables are fully readable offline, but images are loaded from Wikipedia's servers, so they only show up while online.
- If Wikipedia stages a blackout protest, you'll have to black out the pages with a marker yourself.
