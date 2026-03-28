[English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md)

# FinClaw 🦀

**스스로 진화하는 트레이딩 인텔리전스 — 유전 알고리즘이 당신이 상상하지 못한 전략을 발견합니다.**

<p align="center">
  <a href="https://pypi.org/project/finclaw-ai/"><img src="https://img.shields.io/pypi/v/finclaw-ai?color=blue" alt="PyPI"></a>
  <a href="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml"><img src="https://github.com/NeuZhou/finclaw/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/gh/NeuZhou/finclaw"><img src="https://codecov.io/gh/NeuZhou/finclaw/graph/badge.svg" alt="codecov"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+"></a>
  <img src="https://img.shields.io/badge/factors-484-orange" alt="484 Factors">
  <img src="https://img.shields.io/badge/tests-5600%2B-brightgreen" alt="5600+ Tests">
  <img src="https://img.shields.io/badge/markets-crypto%20%7C%20A--shares%20%7C%20US-ff69b4" alt="Crypto + A-shares + US">
  <a href="https://github.com/NeuZhou/finclaw/stargazers"><img src="https://img.shields.io/github/stars/NeuZhou/finclaw?style=social" alt="GitHub Stars"></a>
</p>

<p align="center">
  <img src="assets/hero-finclaw.png" alt="FinClaw — Self-Evolving Trading Intelligence" width="800">
</p>

<p align="center">
  <a href="https://www.youtube.com/watch?v=Y3wY9rj0PmE">
    <img src="https://img.youtube.com/vi/Y3wY9rj0PmE/maxresdefault.jpg" alt="FinClaw Demo Video" width="600">
  </a>
  <br>
  <em>▶️ Watch: How FinClaw's Self-Evolving Engine Works (2 min)</em>
</p>

> FinClaw은 전략을 직접 작성할 필요가 없습니다. 유전 알고리즘이 484차원 팩터 공간에서 **전략을 자율적으로 발견하고 진화**시키며, Walk-Forward 검증과 몬테카를로 시뮬레이션으로 유효성을 확인합니다.

## 면책 조항

이 프로젝트는 **교육 및 연구 목적**으로만 제공됩니다. 투자 조언이 아닙니다. 과거 수익률이 미래 수익을 보장하지 않습니다. 반드시 페이퍼 트레이딩으로 먼저 검증하세요.

---

## 🚀 빠른 시작

```bash
pip install finclaw-ai
finclaw demo          # 모든 기능 체험
finclaw quote AAPL    # 실시간 시세
finclaw quote BTC/USDT # 암호화폐도 지원
```

API 키도, 거래소 계정도, 설정 파일도 필요 없습니다.

---

<details>
<summary>📺 실행 예시 보기 (클릭하여 펼치기)</summary>

```
$ finclaw demo

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
AAPL                 189.84    +2.31  +1.23%  ▃▃▂ ▂▂▂▃▂ ▄▅▅▇█▇▃▄▄▃
NVDA                 875.28   +15.67  +1.82%    ▃▅▄▁▅▆▇█▄▅▆▇▄▄▄▄▅▄
TSLA                 175.21    -3.45  -1.93%  ▅▃▃▃▃▃▄▆▄▄▆▅▆▅▇█▅▃▂ 
MSFT                 415.50    +1.02  +0.25%  ▁▁▂▅▅▄▄▂▃▅▆▆▆▆▇▇▆▃  

━━━ 🚀 Backtest: Momentum Strategy on AAPL ━━━

Strategy:  +75.7%  (+32.5%/yr)    Buy&Hold:  +67.7%
Alpha:     +8.0%                  Sharpe:    1.85
MaxDD:     -8.3%                  Win Rate:  63%
```

</details>

---

## 왜 FinClaw인가?

대부분의 퀀트 도구는 **사용자가 직접** 전략을 작성해야 합니다. FinClaw은 전략을 **자동으로** 진화시킵니다.

| | FinClaw | Freqtrade | Jesse | FinRL / Qlib |
|---|---|---|---|---|
| 전략 설계 | GA가 484차원 DNA 진화 | 사용자가 규칙 작성 | 사용자가 규칙 작성 | DRL로 에이전트 훈련 |
| 지속적 진화 | **전략 자체가 진화** | 봇 가동, 전략 고정 | 봇 가동, 전략 고정 | 학습은 오프라인 |
| Walk-Forward 검증 | ✅ 내장 (70/30 + 몬테카를로) | ❌ 플러그인 필요 | ❌ 플러그인 필요 | ⚠️ 부분적 |
| 과적합 방지 | Arena 경쟁 + 편향 감지 | 기본 교차검증 | 기본적 | 도구에 따라 다름 |
| API 키 불필요 | ✅ `pip install && finclaw demo` | ❌ 거래소 키 필요 | ❌ 키 필요 | ❌ 데이터 설정 필요 |
| 지원 시장 | 암호화폐 + A주 + 미국 주식 | 암호화폐만 | 암호화폐만 | A주 (Qlib) |
| MCP 서버 (AI 에이전트) | ✅ Claude / Cursor / VS Code | ❌ | ❌ | ❌ |
| 팩터 라이브러리 | 484개 팩터, 자동 가중치 | ~50개 수동 지표 | 수동 지표 | Alpha158 (Qlib) |

---

## 📊 484 팩터 차원

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
| 갭 분석 | 8 | 갭 필, 갭 모멘텀, 갭 반전 |
| 시장 폭 | 5 | 등락 지표, 섹터 로테이션, 신고가/신저가 |
| 뉴스 센티먼트 | 2 | EN/ZH 키워드 센티먼트 점수 + 모멘텀 |
| DRL 시그널 | 2 | Q-learning 매수 확률 + 상태 가치 추정 |

> **설계 원칙**: 테크니컬, 센티먼트, DRL, 펀더멘탈 — 모든 시그널은 `[0, 1]`을 반환하는 팩터로 통일됩니다. 가중치는 진화 엔진이 결정하며, 시그널 합성에 사람의 편향이 개입하지 않습니다.

---

## 🧬 자기 진화 엔진

유전 알고리즘이 최적의 전략을 지속적으로 발견합니다:

1. **시드** — 다양한 팩터 가중치 구성으로 초기 모집단 생성
2. **평가** — Walk-Forward 검증으로 각 DNA 백테스트
3. **선택** — 적합도(Sharpe × Return / MaxDrawdown) 상위 유지
4. **돌연변이** — 랜덤 가중치 변동, 교배, 팩터 추가/제거
5. **반복** — 머신에서 7×24 가동

```bash
finclaw evolve --market crypto --generations 50   # 암호화폐 (주요 사용 사례)
finclaw evolve --market cn --generations 50       # A주
finclaw evolve --market crypto --population 50 --mutation-rate 0.2 --elite 10
```

### 진화 결과

| 시장 | 세대 | 연간 수익률 | 샤프 비율 | 최대 낙폭 |
|--------|-----------|---------------|--------|-------------|
| A주 | 89세대 | 2,756% | 6.56 | 26.5% |
| 암호화폐 | 19세대 | 16,066% | 12.19 | 7.2% |

> ⚠️ 이 결과는 과거 데이터 기반 **인샘플** 백테스트 결과입니다. 실제 성과는 크게 낮을 수 있습니다. Walk-Forward 아웃오브샘플 검증은 기본 활성화되어 있습니다 — `finclaw check-backtest`로 결과를 검증하고, `finclaw paper`로 페이퍼 트레이딩 후 실제 자본을 투입하세요.

---

## 🏟️ Arena 모드 (과적합 방지)

기존 백테스팅은 각 전략을 개별 평가하기 때문에, 과적합된 전략이 과거 데이터에서는 좋은 성과를 보이지만 실전에서는 실패합니다. FinClaw의 **Arena 모드**가 이 문제를 해결합니다:

- 여러 DNA 전략이 동일한 시뮬레이션 시장에서 동시에 거래
- **혼잡 페널티**: 50% 이상의 DNA가 같은 시그널로 매수하면 가격 충격 발동
- 고립된 환경에서만 작동하는 과적합 전략은 Arena 순위에서 페널티를 받음

---

## ✅ 품질 보증

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

## 💻 CLI 레퍼런스

FinClaw은 70개 이상의 서브커맨드를 제공합니다. 주요 명령어:

| 명령어 | 설명 |
|---------|-------------|
| `finclaw demo` | 전체 기능 데모 |
| `finclaw quote AAPL` | 실시간 미국 주식 시세 |
| `finclaw quote BTC/USDT` | 암호화폐 시세 (ccxt 경유) |
| `finclaw evolve --market crypto` | 유전 알고리즘 진화 실행 |
| `finclaw backtest -t AAPL` | 주식 전략 백테스트 |
| `finclaw check-backtest` | 백테스트 결과 검증 |
| `finclaw analyze TSLA` | 기술적 분석 |
| `finclaw screen` | 종목 스크리닝 |
| `finclaw risk-report` | 포트폴리오 리스크 리포트 |
| `finclaw sentiment` | 시장 센티먼트 |
| `finclaw copilot` | AI 금융 어시스턴트 |
| `finclaw generate-strategy` | 자연어 → 전략 코드 |
| `finclaw mcp serve` | AI 에이전트용 MCP 서버 |
| `finclaw paper` | 페이퍼 트레이딩 모드 |
| `finclaw doctor` | 환경 점검 |

전체 명령어 목록은 `finclaw --help`로 확인할 수 있습니다.

---

## 🤖 MCP 서버 (AI 에이전트용)

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

## 📡 데이터 소스

| 시장 | 소스 | API 키 필요? |
|--------|--------|-----------------|
| 암호화폐 | ccxt (100+ 거래소) | 불필요 (공개 데이터) |
| 미국 주식 | Yahoo Finance | 불필요 |
| A주 | AKShare + BaoStock | 불필요 |
| 뉴스 센티먼트 | CryptoCompare + AKShare | 불필요 |

---

## 아키텍처

```
┌──────────────────────────────────────────────────────┐
│             Evolution Engine (Core)                   │
│      Genetic Algorithm → Mutate → Backtest → Select   │
│                                                       │
│      Input: 484 factors × weights = DNA               │
│      Output: Walk-forward validated strategy           │
├──────────────────────────────────────────────────────┤
│   Technical(284) │ Sentiment │ DRL │ Davis │ Crypto(200)│
│       All → compute() → [0, 1]                        │
├──────────────────────────────────────────────────────┤
│   Arena Competition │ Bias Detection │ Monte Carlo     │
├──────────────────────────────────────────────────────┤
│   Paper Trading → Live Trading → 100+ Exchanges       │
└──────────────────────────────────────────────────────┘
```

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

## 🌐 에코시스템

FinClaw은 NeuZhou AI 에이전트 툴킷의 일부입니다:

| 프로젝트 | 설명 |
|---------|-------------|
| **[FinClaw](https://github.com/NeuZhou/finclaw)** | AI 네이티브 퀀트 금융 엔진 |
| **[ClawGuard](https://github.com/NeuZhou/clawguard)** | AI 에이전트 면역 시스템 — 285+ 위협 패턴, 의존성 제로 |
| **[AgentProbe](https://github.com/NeuZhou/agentprobe)** | AI 에이전트를 위한 Playwright — 테스트, 기록, 재생 |

---

## 기여하기

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw && pip install -e ".[dev]" && pytest
```

가이드라인은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요. [버그 리포트](https://github.com/NeuZhou/finclaw/issues) · [기능 요청](https://github.com/NeuZhou/finclaw/issues)

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
