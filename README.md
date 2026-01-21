# 🤖 Crypto Futures Auto-Trading Bot

암호화폐 선물 자동매매 시스템 (Binance Futures)

## 🚀 주요 기능

- **3가지 전략**: Breakout, Trend, MeanReversion
- **Kelly Criterion 포지션 사이징**: 동적 리스크 관리
- **펀딩비 최적화**: 펀딩비 역방향 전략
- **실시간 모니터링**: 텔레그램 알림 + 대시보드

## 📁 구조

```
Trading/
├── python_brain/     # 🧠 핵심 트레이딩 로직
│   ├── core/         # 전략, EV추정, 포지션사이징
│   ├── infrastructure/  # 거래소 연동
│   └── monitor/      # 텔레그램, 로거
├── ts_executor/      # ⚡ 거래 실행 서버 (Express)
├── dashboard/        # 📊 모니터링 UI (React)
└── components/       # 🧩 공유 컴포넌트
```

## ⚙️ 설치

### Python (트레이딩 엔진)
```bash
cd python_brain
pip install -r requirements.txt
```

### TypeScript (실행 서버)
```bash
cd ts_executor
npm install
```

### Dashboard
```bash
cd dashboard
npm install
```

## 🔑 환경 변수

### python_brain/.env
```
SYMBOL=BTCUSDT
INTERVAL_SEC=60
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### ts_executor/.env
```
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret
EXECUTOR_AUTH_TOKEN=your_token
PORT=3001
```

## 🏃 실행

```bash
# 1. 실행 서버 시작
cd ts_executor && npm start

# 2. 트레이딩 엔진 시작
cd python_brain && python main.py

# 3. 대시보드 (선택)
cd dashboard && npm run dev
```

## ⚠️ 주의사항

- 실전 투입 전 **백테스트 필수**
- 페이퍼 트레이딩 1주일 권장
- API 키 보안 주의
