# Casper Vehicle Monitor

GitHub Actions 환경에서 현대 캐스퍼 특별기획전 페이지를 주기적으로 확인하고, 신규 차량이 등록되면 Telegram 채널로 알림을 보냅니다.

## 구성

- GitHub Actions: 정기 실행
- Python: 웹페이지/JSON 조회
- Telegram Bot API: 알림 전송
- state.json: 마지막으로 전송한 차량 ID 저장

## 필수 설정

GitHub 저장소의 Secrets에 다음 값을 등록해야 합니다.

- `TELEGRAM_BOT_TOKEN`: Telegram Bot 토큰
- `TELEGRAM_CHAT_ID`: 채널 또는 그룹의 chat id
- `EXHIBITION_NO`: 기본값 `E20260133`

## 로컬 실행

```bash
python -m venv .venv
. .venv\Scripts\activate
pip install -r requirements.txt
set TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
set TELEGRAM_CHAT_ID=YOUR_CHAT_ID
python app/monitor.py
```

## GitHub Actions 자동 실행

워크플로는 10분마다 실행됩니다.

- `.github/workflows/casper-monitor.yml`

수동 실행도 가능합니다.

## 동작 방식

1. Hyundai Casper 전시 API를 조회
2. 현재 차량 목록을 모아서 ID 기준으로 비교
3. 이전에 본 적 없는 차량만 필터링
4. Telegram 메시지 전송
5. `state.json`에 신규 ID를 저장

## 주의

- `state.json`은 GitHub Actions에서 커밋되어 다음 실행 시 재사용됩니다.
- 의도치 않은 중복 전송을 막기 위해 차량 고유 ID 기준으로 판별합니다.
- 홈페이지 구조가 변경되면 `app/casper_client.py`의 파싱 로직을 조정해야 합니다.
