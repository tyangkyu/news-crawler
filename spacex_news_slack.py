import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
from html import escape
from urllib.parse import urlparse

# ── 설정 ──────────────────────────────────────────────
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

RSS_SOURCES = [
    {"name": "Spaceflight Now",  "url": "https://spaceflightnow.com/feed/",        "keyword": "spacex"},
    {"name": "Space.com",        "url": "https://www.space.com/feeds/all",          "keyword": "spacex"},
    {"name": "NASASpaceflight",  "url": "https://www.nasaspaceflight.com/feed/",    "keyword": "spacex"},
]
MAX_RSS_BYTES = 1_000_000
MAX_FIELD_LENGTH = 300
ALLOWED_URL_SCHEMES = {"http", "https"}
# ──────────────────────────────────────────────────────


def clean_text(value, max_length=MAX_FIELD_LENGTH):
    """Slack mrkdwn에 안전하게 넣을 수 있도록 텍스트를 정리."""
    text = " ".join(str(value or "").split())
    if len(text) > max_length:
        text = text[: max_length - 1] + "…"
    return escape(text, quote=False)


def is_safe_url(url):
    text = str(url or "").strip()
    if any(ch.isspace() or ch in "<>|" for ch in text):
        return False
    parsed = urlparse(text)
    return parsed.scheme in ALLOWED_URL_SCHEMES and bool(parsed.netloc)


def slack_article_link(url, title):
    safe_title = clean_text(title)
    if is_safe_url(url):
        return f"<{url.strip()}|{safe_title}>"
    return safe_title


def require_slack_webhook(webhook_url):
    if not webhook_url or not is_safe_url(webhook_url):
        raise RuntimeError("SLACK_WEBHOOK_URL 환경변수에 유효한 Slack Webhook URL을 설정해야 합니다.")
    return webhook_url


def validate_rss_response(response):
    content_type = response.headers.get("Content-Type", "").lower()
    if content_type and not any(token in content_type for token in ("xml", "rss", "atom", "text")):
        raise ValueError(f"RSS가 아닌 응답 Content-Type: {content_type}")
    if len(response.content) > MAX_RSS_BYTES:
        raise ValueError(f"RSS 응답이 너무 큽니다: {len(response.content)} bytes")


def fetch_rss(source, max_items=8):
    results = []
    try:
        if not is_safe_url(source["url"]):
            raise ValueError(f"허용되지 않은 RSS URL: {source['url']}")

        res = requests.get(source["url"], headers=HEADERS, timeout=10)
        res.raise_for_status()
        validate_rss_response(res)
        soup = BeautifulSoup(res.content, "xml")

        for item in soup.find_all("item"):
            title    = item.find("title")
            link     = item.find("link")
            pub_date = item.find("pubDate") or item.find("dc:date")

            title_text = title.get_text(strip=True)   if title    else ""
            link_text  = link.get_text(strip=True)    if link     else ""
            date_text  = pub_date.get_text(strip=True) if pub_date else "날짜 없음"

            if source["keyword"].lower() not in title_text.lower():
                continue

            try:
                dt = datetime.strptime(date_text[:25], "%a, %d %b %Y %H:%M:%S")
                date_text = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

            results.append({"title": title_text, "link": link_text, "date": date_text})
            if len(results) >= max_items:
                break

    except Exception as e:
        print(f"  [{source['name']}] RSS 오류: {e}")
    return results


def build_slack_blocks(source_name, articles):
    """소스 1개 분량의 Slack Block Kit 메시지를 반환."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🚀 SpaceX 뉴스 — {source_name}", "emoji": True},
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
        article_link = slack_article_link(a.get("link"), a.get("title"))
        date = clean_text(a.get("date", "날짜 없음"), 80)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{i}. {article_link}*\n🗓 {date}",
            },
        })

    blocks.append({"type": "divider"})
    return blocks


def send_to_slack(blocks, webhook_url):
    payload = {"blocks": blocks}
    try:
        webhook_url = require_slack_webhook(webhook_url)
        res = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if res.status_code == 200:
            print("  → Slack 발송 성공")
        else:
            print(f"  → Slack 발송 실패: {res.status_code} {res.text[:200]}")
    except Exception as e:
        print(f"  → Slack 발송 오류: {e}")


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("=" * 65)
    print(f"  SpaceX 뉴스 크롤러 + Slack 발송  ({now})")
    print("=" * 65)

    # 인트로 헤더 블록을 한 번만 전송
    intro_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🛸 SpaceX 최신 뉴스 브리핑*\n수집 시각: {now}",
            },
        },
        {"type": "divider"},
    ]
    print("\n[인트로 메시지 발송]")
    send_to_slack(intro_blocks, SLACK_WEBHOOK_URL)

    for source in RSS_SOURCES:
        print(f"\n[{source['name']}] 크롤링 중...")
        articles = fetch_rss(source)
        print(f"  {len(articles)}건 수집")

        blocks = build_slack_blocks(source["name"], articles)
        send_to_slack(blocks, SLACK_WEBHOOK_URL)

    print("\n완료.")


if __name__ == "__main__":
    main()
