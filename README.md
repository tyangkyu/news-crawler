# ICT News Crawler

RSS와 Google News RSS에서 주요 IT·우주 산업 뉴스를 수집해 Slack Incoming Webhook으로 전송하는 Python 스크립트 모음입니다.

## 포함된 스크립트

- `news_crawler.py`: IT 산업 키워드별 뉴스 브리핑을 수집하고 Slack으로 전송합니다.
- `spacex_news.py`: SpaceX 관련 RSS 뉴스를 콘솔에서 확인하는 용도입니다.
- `spacex_news_slack.py`: SpaceX 관련 RSS 뉴스를 Slack으로 전송합니다.

## 설치

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## 환경변수

```bash
cp .env.example .env
```

`.env` 또는 실행 환경에 아래 값을 설정합니다.

| 이름 | 필수 | 설명 |
|---|---:|---|
| `SLACK_WEBHOOK_URL` | 예 | Slack Incoming Webhook URL |

민감 정보가 들어 있는 `.env`, 실행 로그, 로컬 실행 스크립트는 GitHub에 올리지 않습니다.

## 실행

```bash
python news_crawler.py
python spacex_news_slack.py
```

Slack 전송 없이 SpaceX RSS 수집 로직만 확인하려면:

```bash
python spacex_news.py
```

## 보안 및 운영 주의사항

- Slack Webhook URL은 비밀값입니다. 코드, README, 이슈, 로그에 직접 붙여 넣지 마세요.
- `.env.example`에는 실제 값 대신 placeholder만 둡니다.
- RSS 응답 크기와 URL scheme 검증이 포함되어 있지만, 외부 RSS 장애나 포맷 변경은 발생할 수 있습니다.
- 반복 실행은 cron, launchd, GitHub Actions 등에서 환경변수 Secret을 주입하는 방식으로 구성하세요.
