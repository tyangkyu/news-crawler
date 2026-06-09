# ICT-news-clipper
주요 IT 산업 키워드를 크롤링해서 Slack 채널로 보내주는 기능

## 설정

```bash
pip install -r requirements.txt
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
python news_crawler.py
```

`SLACK_WEBHOOK_URL`은 저장소에 커밋하지 말고 환경변수나 비밀 관리 도구로만 주입하세요. Webhook이 노출되면 Slack에서 즉시 회전하세요.

## 보안 메모

- RSS 응답은 `http`/`https` URL만 허용하고, 비정상 Content-Type 또는 1MB 초과 응답은 거부합니다.
- Slack 메시지에 들어가는 RSS 제목/출처/날짜는 `mrkdwn` 특수문자를 escape합니다.
- `.env`, 로그, 로컬 도구 메타데이터는 `.gitignore`에 포함했습니다.
