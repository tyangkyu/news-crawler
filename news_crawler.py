import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os

# ── 설정 ──────────────────────────────────────────────
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

KEYWORDS = ["SpaceX", "삼성전자", "SK하이닉스"]

# 키워드별 RSS 소스 정의
# sources 미지정 시 Google News RSS만 사용
KEYWORD_SOURCES = {
    "SpaceX": [
        {"name": "Spaceflight Now", "url": "https://spaceflightnow.com/feed/",     "lang": "en"},
        {"name": "Space.com",       "url": "https://www.space.com/feeds/all",       "lang": "en"},
        {"name": "Google News",     "url": None,                                    "lang": "en"},
    ],
    "삼성전자": [
        {"name": "Google News",     "url": None,                                    "lang": "ko"},
    ],
    "SK하이닉스": [
        {"name": "Google News",     "url": None,                                    "lang": "ko"},
    ],
}

MAX_ITEMS = 5  # 소스별 최대 기사 수

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
# ──────────────────────────────────────────────────────


def google_news_rss_url(keyword, lang="ko"):
    """Google News RSS URL 생성."""
    hl = "ko" if lang == "ko" else "en"
    gl = "KR" if lang == "ko" else "US"
    ceid = "KR:ko" if lang == "ko" else "US:en"
    return (
        f"https://news.google.com/rss/search"
        f"?q={requests.utils.quote(keyword)}&hl={hl}&gl={gl}&ceid={ceid}"
    )


def parse_date(date_str):
    """pubDate 문자열을 YYYY-MM-DD HH:MM으로 정규화."""
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(date_str[:31].strip(), fmt).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return date_str.strip()


def fetch_rss(url, keyword, max_items=MAX_ITEMS):
    """RSS URL에서 keyword 포함 기사를 크롤링."""
    results = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, "xml")

        for item in soup.find_all("item"):
            title_el    = item.find("title")
            link_el     = item.find("link")
            pub_date_el = item.find("pubDate") or item.find("dc:date")
            source_el   = item.find("source")

            title = title_el.get_text(strip=True)    if title_el    else ""
            link  = link_el.get_text(strip=True)     if link_el     else ""
            date  = parse_date(pub_date_el.get_text()) if pub_date_el else "날짜 없음"
            outlet = source_el.get_text(strip=True)  if source_el   else ""

            # keyword 필터 (Google News는 이미 검색 결과이므로 필터 완화)
            if keyword.lower() not in title.lower() and "news.google.com" not in url:
                continue

            results.append({"title": title, "link": link, "date": date, "outlet": outlet})
            if len(results) >= max_items:
                break

    except Exception as e:
        print(f"    오류: {e}")
    return results


def crawl_keyword(keyword):
    """키워드에 해당하는 모든 소스에서 기사를 수집, 중복 제거 후 반환."""
    sources = KEYWORD_SOURCES.get(keyword, [{"name": "Google News", "url": None, "lang": "ko"}])
    all_articles = []
    seen_titles = set()

    for src in sources:
        url = src["url"] if src["url"] else google_news_rss_url(keyword, src.get("lang", "ko"))
        print(f"  [{src['name']}] 크롤링 중...")
        articles = fetch_rss(url, keyword)

        for a in articles:
            if a["title"] not in seen_titles:
                seen_titles.add(a["title"])
                a["source"] = src["name"]
                all_articles.append(a)

        print(f"    → {len(articles)}건 수집")

    return all_articles


def build_slack_blocks(keyword, articles):
    """키워드 1개 분량의 Slack Block Kit 메시지 생성."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📰 {keyword} 뉴스 브리핑", "emoji": True},
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"수집 시각: {now}  |  총 {len(articles)}건"}],
        },
        {"type": "divider"},
    ]

    if not articles:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_수집된 기사가 없습니다._"},
        })
        return blocks

    for i, a in enumerate(articles, 1):
        outlet_tag = f"  `{a['outlet']}`" if a.get("outlet") else ""
        source_tag = f"  — _{a.get('source', '')}_"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{i}. <{a['link']}|{a['title']}>*\n"
                    f"🗓 {a['date']}{outlet_tag}{source_tag}"
                ),
            },
        })

    blocks.append({"type": "divider"})
    return blocks


def send_to_slack(blocks, webhook_url=SLACK_WEBHOOK_URL):
    payload = {"blocks": blocks}
    try:
        res = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if res.status_code == 200:
            print("  → Slack 발송 성공")
        else:
            print(f"  → Slack 발송 실패: {res.status_code} {res.text}")
    except Exception as e:
        print(f"  → Slack 발송 오류: {e}")


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("=" * 65)
    print(f"  범용 뉴스 크롤러  ({now})")
    print(f"  키워드: {', '.join(KEYWORDS)}")
    print("=" * 65)

    for keyword in KEYWORDS:
        print(f"\n[키워드: {keyword}]")
        articles = crawl_keyword(keyword)
        print(f"  총 {len(articles)}건 (중복 제거 후)")

        blocks = build_slack_blocks(keyword, articles)
        send_to_slack(blocks)

    print("\n완료.")


if __name__ == "__main__":
    main()
