[English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md)

# FinClaw 🦀

**스스로 진화하는 트레이딩 인텔리전스 — 유전 알고리즘(GA)이 당신이 상상하지 못한 전략을 발견합니다.**

<p align="center">
  <a href="https://pypi.org/project/finclaw-ai/"><img src="https://img.shields.io/pypi/v/finclaw-ai?color=blue" alt="PyPI"></a>
  <a href="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml"><img src="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+"></a>
  <img src="https://img.shields.io/badge/factors-484-orange" alt="484 Factors">
  <img src="https://img.shields.io/badge/tests-5600%2B-brightgreen" alt="5600+ Tests">
  <img src="https://img.shields.io/badge/markets-crypto%20%7C%20A--shares%20%7C%20US-ff69b4" alt="Crypto + A-shares + US">
  <a href="https://github.com/NeuZhou/finclaw/stargazers"><img src="https://img.shields.io/github/stars/NeuZhou/finclaw?style=social" alt="GitHub Stars"></a>
</p>

> FinClaw은 전략을 직접 작성할 필요가 없습니다. 유전 알고리즘(GA)이 484차원 팩터 공간에서 **전략을 자율적으로 발견하고 진화**시키며, Walk-Forward 검증과 몬테카를로 시뮬레이션으로 유효성을 확인합니다.

<p align="center">
  <img src="assets/demo-evolve.svg" alt="FinClaw Evolution Demo" width="800">
</p>

## 면책 조항

이 프로젝트는 **교육 및 연구 목적**으로만 제공됩니다. 투자 조언이 아닙니다. 과거 수익률이 미래 수익을 보장하지 않습니다. 반드시 페이퍼 트레이딩으로 먼저 검증하세요.

---

## 빠른 시작

```bash
pip install -e .

# 모든 기능을 체험 — API 키 불필요
finclaw demo

# 암호화폐 시장 데이터 다운로드
finclaw download-crypto --coins BTC,ETH,SOL --days 365

# 유전 알고리즘으로 암호화폐 전략 진화
finclaw evolve --market crypto --generations 50

# 실시간 시세
finclaw quote BTC/USDT
finclaw quote AAPL
```

이게 전부입니다. API 키도, 거래소 계정도, 설정 파일도 필요 없습니다.

### 실행 예시

<details>
<summary><code>finclaw demo</code> — 전체 기능 쇼케이스</summary>

```
███████╗██╗███╗   ██╗ ██████╗██╗      █████╗ ██╗    ██╗
██╔════╝██║████╗  ██║██╔════╝██║     ██╔══██╗██║    ██║
█████╗  ██║██╔██╗ ██║██║     ██║     ███████║██║ █╗ ██║
██╔══╝  ██║██║╚██╗██║██║     ██║     ██╔══██║██║███╗██║
██║     ██║██║ ╚████║╚██████╗███████╗██║  ██║╚███╔███╔╝
╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝
AI-Powered Financial Intelligence Engine

🎬 FinClaw Demo — All features, zero config

━━━ 📊 Real-Time Quotes ━━━

Symbol        Price     Change        %                 Trend
────────────────────────────────────────────────────────────
AAPL                 189.84    +2.31  +1.23%  ▇█▇▆▅▅▅▄▄▄▃▃▂▁   ▁▁▁
NVDA                 875.28   +15.67  +1.82%  ▄▄▆▅▅▃▂▂  ▂▃▃▁▄▅▆▅▇▆
TSLA                 175.21    -3.45  -1.93%    ▁▁▁▂▄▄▄▄▄▂▃▃▃▄▃▄▅▇
MSFT                 415.50    +1.02  +0.25%  █▇▇▆▄▅▅▅▅▄▅▄▂▂     ▁

━━━ 🚀 Backtest: Momentum Strategy on AAPL ━━━

Strategy:  +75.7%  (+32.5%/yr)    Buy&Hold:  +67.7%
Alpha:     +8.0%                  Sharpe:    1.85
MaxDD:     -8.3%                  Win Rate:  63%

━━━ 🤖 AI Features ━━━

MCP Server  — Expose FinClaw as tools for Claude, Cursor, VS Code
Copilot     — Interactive AI financial assistant
Strategy AI — Natural language → trading code
```

</details>

<details>
<summary><code>finclaw quote BTC/USDT</code> — 실시간 암호화폐 시세</summary>

```
BTC/USDT  $68828.00   -3.53%
Bid: 68828.0  Ask: 68828.1  Vol: 455,860,493
```

</details>

<details>
<summary><code>finclaw evolve --market crypto --generations 50</code> — 전략 진화</summary>

```
🧬 Evolution Engine — Crypto Market
  Population: 30  |  Mutation Rate: 0.3  |  Elite: 5

  Gen  1 │ Best: 0.342 │ Avg: 0.118 │ Sharpe: 0.89 │ ░░░░░░░░░░
  Gen  5 │ Best: 0.567 │ Avg: 0.234 │ Sharpe: 1.12 │ ██░░░░░░░░
  Gen 10 │ Best: 0.723 │ Avg: 0.389 │ Sharpe: 1.45 │ ████░░░░░░
  Gen 25 │ Best: 0.891 │ Avg: 0.512 │ Sharpe: 1.87 │ ██████░░░░
  Gen 50 │ Best: 0.934 │ Avg: 0.601 │ Sharpe: 2.14 │ ████████░░

  ✅ Best DNA saved to evolution_results/best_gen50.json
```

</details>

---

## 왜 FinClaw인가?

대부분의 퀀트 도구는 **사용자가 직접** 전략을 작성해야 합니다. FinClaw은 전략을 **자동으로** 진화시킵니다.

| | FinClaw | Freqtrade | Jesse | FinRL / Qlib |
|---|---|---|---|---|
| 전략 설계 | GA가 484차원 DNA를 진화 | 사용자가 규칙 작성 | 사용자가 규칙 작성 | 심층강화학습으로 에이전트 훈련 |
| 상시 가동 | **전략 자체가 진화** | 봇 가동, 전략 고정 | 봇 가동, 전략 고정 | 학습은 오프라인 |
| Walk-Forward 검증 | ✅ 내장 (70/30 + 몬테카를로) | ❌ 플러그인 필요 | ❌ 플러그인 필요 | ⚠️ 부분적 |
| 과적합 방지 | Arena 경쟁 + 편향 감지 | 기본 교차검증 | 기본적 | 도구에 따라 다름 |
| API 키 없이 시작 | ✅ `pip install && finclaw demo` | ❌ 거래소 키 필요 | ❌ 키 필요 | ❌ 데이터 설정 필요 |
| 지원 시장 | 암호화폐 + 중국 A주 + 미국 주식 | 암호화폐만 | 암호화폐만 | 중국 A주 (Qlib) |
| MCP 서버 (AI 에이전트) | ✅ Claude / Cursor / VS Code | ❌ | ❌ | ❌ |
| 팩터 라이브러리 | 484개 팩터, 자동 가중치 | ~50개 수동 지표 | 수동 지표 | Alpha158 (Qlib) |

### FinClaw만의 차별점

- **자기 진화 팩터** — 유전 알고리즘(GA)이 484차원에서 전략 DNA의 돌연변이, 교배, 선택을 수행합니다. 시그널 가중치를 사람이 결정하는 것이 아니라, 자연선택이 결정합니다.
- **Walk-Forward 검증** — 모든 백테스트는 70/30 학습/테스트 분할과 몬테카를로 시뮬레이션(1,000회 반복, p < 0.05)을 사용합니다. 단순한 인샘플 백테스팅이 아닌, 기관 투자자 수준의 검증 방법론입니다.
- **멀티마켓** — 암호화폐(ccxt 경유, 100개 이상 거래소), 중국 A주(AKShare + BaoStock), 미국 주식(Yahoo Finance). 하나의 엔진으로 모든 시장을 커버합니다.
- **AI 네이티브** — MCP 서버를 내장하여 Claude, Cursor, VS Code에서 시세 조회, 백테스트 실행, 포트폴리오 분석을 네이티브로 수행할 수 있습니다.

---

## 아키텍처

```
┌──────────────────────────────────────────────────────┐
│             진화 엔진 (코어)                            │
│      유전 알고리즘 → 돌연변이 → 백테스트 → 선택          │
│                                                       │
│      입력: 484 팩터 × 가중치 = DNA                     │
│      출력: Walk-Forward 검증된 전략                     │
├──────────────────────────────────────────────────────┤
│                 팩터 소스                               │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│   │ 테크니컬  │ │ 센티먼트  │ │   DRL    │ │ Davis  │ │
│   │  284     │ │  뉴스    │ │Q-learning│ │Double  │ │
│   │  범용    │ │  EN / ZH │ │  시그널  │ │ Play   │ │
│   └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
│        └─────────────┴────────────┴────────────┘      │
│   + 200개 암호화폐 전용 팩터                             │
│                모두 → compute() → [0, 1]               │
├──────────────────────────────────────────────────────┤
│               품질 보증                                 │
│   ┌────────────┐ ┌─────────────┐ ┌────────────────┐  │
│   │   Arena    │ │    편향     │ │  Walk-Forward  │  │
│   │   경쟁     │ │    감지     │ │ + 몬테카를로    │  │
│   └────────────┘ └─────────────┘ └────────────────┘  │
├──────────────────────────────────────────────────────┤
│               실행 레이어                               │
│   페이퍼 트레이딩 → 라이브 트레이딩 → 100+ 거래소         │
└──────────────────────────────────────────────────────┘
```

---

## 팩터 라이브러리 (484개 팩터)

284개 범용 팩터 + 200개 암호화폐 전용 팩터, 카테고리별 구성:

| 카테고리 | 수 | 예시 |
|----------|-------|---------|
| 암호화폐 전용 | 200 | 펀딩비율 프록시, 세션 효과, 고래 감지, 연쇄 청산 |
| 모멘텀 | 14 | ROC, 가속도, 추세 강도, 퀄리티 모멘텀 |
| 거래량 & 유동성 | 13 | OBV, 스마트 머니, 거래량-가격 괴리, Wyckoff VSA |
| 변동성 | 13 | ATR, 볼린저 스퀴즈, 레짐 감지, 변동성의 변동성 |
| 평균 회귀 | 12 | Z점수, 러버밴드, 켈트너 포지션 |
| 추세 추종 | 14 | ADX, EMA 골든크로스, 고가·저가 갱신, MA 팬 |
| Qlib Alpha158 | 11 | KMID, KSFT, CNTD, CORD, SUMP (Microsoft Qlib 호환) |
| 퀄리티 필터 | 11 | 수익 모멘텀 프록시, 상대 강도, 레질리언스 |
| 리스크 경고 | 11 | 연속 손실, 데드크로스, 갭다운, 하한가 |
| 천정 탈출 | 10 | 분배 감지, 클라이맥스 거래량, 스마트 머니 이탈 |
| 가격 구조 | 10 | 캔들 패턴, 지지/저항, 피봇 포인트 |
| Davis Double Play | 8 | 매출 가속, 기술 해자, 공급 소진 |
| 알파 | 10 | 다양한 알파 팩터 구현 |
| 갭 분석 | 8 | 갭 필, 갭 모멘텀, 갭 반전 |
| 시장 폭 | 5 | 등락 지표, 섹터 로테이션, 신고가/신저가 |
| 뉴스 센티먼트 | 2 | EN/ZH 키워드 센티먼트 점수 + 모멘텀 |
| DRL 시그널 | 2 | Q-learning 매수 확률 + 상태 가치 추정 |
| ... 기타 다수 | 130 | 펀더멘탈 프록시, 풀백, 바닥 확인, 레짐 등 |

> **설계 원칙**: 테크니컬, 센티먼트, DRL, 펀더멘탈 등 모든 시그널은 `[0, 1]`을 반환하는 팩터로 통일됩니다. 가중치는 진화 엔진이 결정하며, 시그널 합성에 사람의 편향이 개입하지 않습니다.

---

## 진화 엔진

유전 알고리즘(GA)이 최적의 전략을 지속적으로 발견합니다:

1. **시드** — 다양한 팩터 가중치 구성으로 초기 모집단 생성
2. **평가** — Walk-Forward 검증으로 각 DNA를 백테스트
3. **선택** — 상위 성과자 유지
4. **돌연변이** — 랜덤 가중치 변동, 교배, 팩터 추가/제거
5. **반복** — 머신에서 24시간 365일 가동

```bash
# 암호화폐 (주요 사용 사례)
finclaw evolve --market crypto --generations 50

# 중국 A주
finclaw evolve --market cn --generations 50

# 커스텀 파라미터 지정
finclaw evolve --market crypto --population 50 --mutation-rate 0.2 --elite 10
```

### 진화 결과

| 시장 | 세대 | 연간 수익률 | 샤프 비율 | 최대 낙폭 |
|--------|-----------|---------------|--------|-------------|
| 중국 A주 | 89세대 | 2,756% | 6.56 | 26.5% |
| 암호화폐 | 19세대 | 16,066% | 12.19 | 7.2% |

> ⚠️ **이 결과는 과거 데이터 기반 인샘플 백테스트 결과입니다**. 실제 성과는 이보다 크게 낮을 수 있습니다. Walk-Forward 아웃오브샘플 검증은 기본적으로 활성화되어 있습니다 — 진화된 전략을 신뢰하기 전에 반드시 OOS 지표를 확인하세요. `finclaw check-backtest`로 결과를 검증하고, 실제 자본을 투입하기 전에 `finclaw paper`로 페이퍼 트레이딩하세요.

---

## Arena 모드 (과적합 방지)

기존 백테스팅은 각 전략을 개별 평가하기 때문에, 과적합된 전략이 과거 데이터에서는 좋은 성과를 보이지만 실전에서는 실패합니다. FinClaw의 **Arena 모드**([FinEvo](https://arxiv.org)에서 영감)가 이 문제를 해결합니다:

```
┌──────────────────────────────────────────┐
│         Arena: 공유 시장 시뮬레이션         │
│                                           │
│   DNA-1 ──┐                              │
│   DNA-2 ──┤── 동일 OHLCV 데이터            │
│   DNA-3 ──┤── 동일 초기 자본               │
│   DNA-4 ──┤── 혼잡 시 가격 충격 발생        │
│   DNA-5 ──┘── 최종 손익으로 순위 결정        │
│                                           │
│   과적합 DNA → 낮은 순위 → 페널티           │
└──────────────────────────────────────────┘
```

- 여러 DNA 전략이 동일한 시뮬레이션 시장에서 동시에 거래
- **혼잡 페널티**: 50% 이상의 DNA 전략이 같은 시그널로 매수하면 가격 충격이 발동
- 고립된 환경에서만 작동하는 과적합 전략은 Arena 순위에서 페널티를 받음

---

## 편향 감지

결과를 신뢰하기 전에 백테스팅의 흔한 함정을 검출합니다:

```bash
python -m src.evolution.bias_cli --all
```

| 검사 항목 | 검출 내용 |
|-------|----------------|
| **선행 편향** | 미래 데이터를 실수로 참조하는 팩터 |
| **데이터 스누핑** | 학습 데이터에서 테스트 데이터의 3배 이상 성과를 내는 DNA (과적합) |
| **생존자 편향** | 백테스트 기간 중 상장폐지된 자산 |

---

## CLI 레퍼런스

FinClaw은 70개 이상의 서브커맨드를 제공합니다. 주요 명령어를 소개합니다:

```bash
# 시세 & 데이터
finclaw quote AAPL              # 미국 주식 시세
finclaw quote BTC/USDT          # 암호화폐 시세 (ccxt 경유)
finclaw history NVDA            # 과거 데이터
finclaw download-crypto         # 암호화폐 OHLCV 데이터 다운로드
finclaw exchanges list          # 지원 거래소 표시

# 진화 & 백테스팅
finclaw evolve --market crypto  # 유전 알고리즘 진화 실행
finclaw backtest -t AAPL        # 주식에 대한 전략 백테스트
finclaw check-backtest          # 백테스트 결과 검증

# 분석 & 도구
finclaw analyze TSLA            # 기술적 분석
finclaw screen                  # 종목 스크리닝
finclaw risk-report             # 포트폴리오 리스크 리포트
finclaw sentiment               # 시장 센티먼트
finclaw demo                    # 전체 기능 데모
finclaw doctor                  # 환경 점검

# AI 기능
finclaw copilot                 # AI 금융 어시스턴트
finclaw generate-strategy       # 자연어 → 전략 코드
finclaw mcp serve               # AI 에이전트용 MCP 서버

# 페이퍼 트레이딩
finclaw paper                   # 페이퍼 트레이딩 모드
finclaw paper-report            # 페이퍼 트레이딩 결과
```

전체 명령어 목록은 `finclaw --help`로 확인할 수 있습니다.

---

## MCP 서버 (AI 에이전트용)

FinClaw을 Claude, Cursor, VS Code 또는 MCP 호환 클라이언트를 위한 도구로 노출:

```json
{
  "mcpServers": {
    "finclaw": {
      "command": "finclaw",
      "args": ["mcp", "serve"]
    }
  }
}
```

10개 도구 제공: `get_quote`, `get_history`, `list_exchanges`, `run_backtest`, `analyze_portfolio`, `get_indicators`, `screen_stocks`, `get_sentiment`, `compare_strategies`, `get_funding_rates`.

---

## 데이터 소스

| 시장 | 소스 | API 키 필요? |
|--------|--------|-----------------|
| 암호화폐 | ccxt (100+ 거래소) | 불필요 (공개 데이터) |
| 미국 주식 | Yahoo Finance | 불필요 |
| 중국 A주 | AKShare + BaoStock | 불필요 |
| 뉴스 센티먼트 | CryptoCompare + AKShare | 불필요 |

---

## 대시보드

```bash
cd dashboard && npm install && npm run dev
# http://localhost:3000 열기
```

- 실시간 가격 (암호화폐, 미국 주식, 중국 A주)
- TradingView 프로페셔널 차트
- 실시간 P&L 포트폴리오 트래커
- 필터 + CSV 내보내기 종목 스크리너
- AI 챗 어시스턴트 (OpenAI, Anthropic, DeepSeek, Ollama)

---

## 검증 및 품질 보증

- Walk-Forward 검증 (70/30 학습/테스트 분할)
- 몬테카를로 시뮬레이션 (1,000회 반복, p값 < 0.05)
- 부트스트랩 95% 신뢰 구간
- Arena 경쟁 (멀티 DNA 시장 시뮬레이션)
- 편향 감지 (선행, 스누핑, 생존자)
- 팩터 IC/IR 분석 및 감쇠 곡선
- 팩터 직교 행렬 (중복 팩터 자동 제거)
- 적합도 함수의 회전율 페널티
- 5,600+ 자동화 테스트

---

## 로드맵

- [x] 484 팩터 진화 엔진
- [x] Walk-Forward 검증 + 몬테카를로
- [x] Arena 경쟁 모드
- [x] 편향 감지 스위트
- [x] 뉴스 센티먼트 + DRL 팩터
- [x] Davis Double Play 팩터
- [x] 페이퍼 트레이딩 인프라
- [x] AI 에이전트용 MCP 서버
- [ ] DEX 실행 (Uniswap V3 / Arbitrum)
- [ ] 멀티 타임프레임 지원 (1h/4h/1d)
- [ ] 가격 시퀀스용 파운데이션 모델

---

## 기여하기

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw && pip install -e ".[dev]"
pytest
```

기여를 환영합니다! 가이드라인은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

**기여 방법:**
- 🐛 [버그 리포트](https://github.com/NeuZhou/finclaw/issues)
- 💡 [기능 요청](https://github.com/NeuZhou/finclaw/issues)
- 🔧 풀 리퀘스트 제출
- 📝 문서 개선
- ⭐ 유용하다면 스타를 눌러주세요

---

## 제한 사항

FinClaw은 연구 및 교육 도구입니다. 주요 제한 사항:

- **무료 데이터 소스** — 지연, 누락, API 속도 제한의 영향을 받습니다
- **단순화된 백테스팅** — 호가창 깊이, 부분 체결, 시장 미시구조를 모델링하지 않습니다
- **인샘플 편향** — 진화된 전략이 아웃오브샘플에서 동일하게 작동하지 않을 수 있습니다. 반드시 Walk-Forward OOS 결과를 확인하세요
- **드라이런 우선** — 실제 자본을 투입하기 전에 반드시 페이퍼 트레이딩으로 전략을 검증하세요

실전 트레이딩에서는 적절한 리스크 관리와 포지션 사이징을 병행하세요.

---

## 라이선스

[MIT](LICENSE)

---

## Star History

<a href="https://www.star-history.com/#NeuZhou/finclaw&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date&theme=dark" />
    <img alt="Star History" src="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date" />
  </picture>
</a>
