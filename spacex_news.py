import requests
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# RSS 피드 기반 소스 (봇 차단 없음)
RSS_SOURCES = [
    {
        "name": "Spaceflight Now",
        "url": "https://spaceflightnow.com/feed/",
        "keyword": "spacex",
    },
    {
        "name": "Space.com",
        "url": "https://www.space.com/feeds/all",
        "keyword": "spacex",
    },
    {
        "name": "NASASpaceflight",
        "url": "https://www.nasaspaceflight.com/feed/",
        "keyword": "spacex",
    },
]


def fetch_rss(source, max_items=8):
    results = []
    try:
        res = requests.get(source["url"], headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, "xml")

        items = soup.find_all("item")
        for item in items:
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubDate") or item.find("dc:date")

            title_text = title.get_text(strip=True) if title else ""
            link_text = link.get_text(strip=True) if link else ""
            date_text = pub_date.get_text(strip=True) if pub_date else "날짜 없음"

            # keyword 필터링 (대소문자 무시)
            if source["keyword"].lower() not in title_text.lower():
                continue

            # 날짜 포맷 정리
            try:
                dt = datetime.strptime(date_text[:25], "%a, %d %b %Y %H:%M:%S")
                date_text = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

            results.append({
                "source": source["name"],
                "title": title_text,
                "link": link_text,
                "date": date_text,
            })

            if len(results) >= max_items:
                break

    except Exception as e:
        print(f"  [{source['name']}] 오류: {e}")
    return results


def print_results(articles):
    if not articles:
        print("  수집된 기사가 없습니다.\n")
        return
    for i, a in enumerate(articles, 1):
        print(f"  {i:2}. {a['title']}")
        print(f"      날짜 : {a['date']}")
        print(f"      링크 : {a['link']}")
        print()


def main():
    print("=" * 65)
    print(f"  SpaceX 최신 뉴스 크롤러  (실행: {datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 65)

    for source in RSS_SOURCES:
        print(f"\n[{source['name']}]")
        articles = fetch_rss(source)
        print_results(articles)


if __name__ == "__main__":
    main()
