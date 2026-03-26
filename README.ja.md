[English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [中文](README.zh-CN.md)

# FinClaw 🦀

**自己進化する投資インテリジェンス — 遺伝的アルゴリズム(GA)があなたの想像を超える戦略を発見します。**

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

> FinClawは戦略の手動設計を必要としません。遺伝的アルゴリズム(GA)が484次元のファクター空間で**戦略を自律的に発見・進化**させ、Walk-Forward検証とモンテカルロ・シミュレーションで有効性を検証します。

<p align="center">
  <img src="assets/demo-evolve.svg" alt="FinClaw Evolution Demo" width="800">
</p>

## 免責事項

本プロジェクトは**教育・研究目的のみ**を対象としています。投資助言ではありません。過去のパフォーマンスが将来の結果を保証するものではありません。必ず最初にペーパートレードで検証してください。

---

## クイックスタート

```bash
pip install -e .

# すべての機能を体験 — APIキー不要
finclaw demo

# 暗号資産の市場データをダウンロード
finclaw download-crypto --coins BTC,ETH,SOL --days 365

# 遺伝的アルゴリズムで暗号資産戦略を進化
finclaw evolve --market crypto --generations 50

# リアルタイム相場
finclaw quote BTC/USDT
finclaw quote AAPL
```

以上です。APIキーも取引所アカウントも設定ファイルも不要です。

### 実行例

<details>
<summary><code>finclaw demo</code> — 全機能のショーケース</summary>

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
<summary><code>finclaw quote BTC/USDT</code> — リアルタイム暗号資産相場</summary>

```
BTC/USDT  $68828.00   -3.53%
Bid: 68828.0  Ask: 68828.1  Vol: 455,860,493
```

</details>

<details>
<summary><code>finclaw evolve --market crypto --generations 50</code> — 戦略の進化</summary>

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

## なぜ FinClaw なのか？

多くのクオンツツールは**あなた自身が**戦略を書く必要があります。FinClawは戦略を**あなたのために**進化させます。

| | FinClaw | Freqtrade | Jesse | FinRL / Qlib |
|---|---|---|---|---|
| 戦略設計 | GAが484次元DNAを進化 | ユーザーがルールを記述 | ユーザーがルールを記述 | 深層強化学習でエージェントを訓練 |
| 常時稼働 | **戦略自体が進化し続ける** | ボット稼働、戦略は固定 | ボット稼働、戦略は固定 | 学習はオフライン |
| Walk-Forward検証 | ✅ 内蔵 (70/30 + モンテカルロ) | ❌ プラグインが必要 | ❌ プラグインが必要 | ⚠️ 部分的 |
| 過学習対策 | Arena競争 + バイアス検出 | 基本的なクロスバリデーション | 基本的 | ツールによる |
| APIキー不要で開始 | ✅ `pip install && finclaw demo` | ❌ 取引所キーが必要 | ❌ キーが必要 | ❌ データセットアップが必要 |
| 対応市場 | 暗号資産 + 中国A株 + 米国株 | 暗号資産のみ | 暗号資産のみ | 中国A株 (Qlib) |
| MCPサーバー (AIエージェント) | ✅ Claude / Cursor / VS Code | ❌ | ❌ | ❌ |
| ファクターライブラリ | 484ファクター、自動重み付け | 約50のテクニカル指標 | 手動指標 | Alpha158 (Qlib) |

### FinClawの独自性

- **自己進化ファクター** — 遺伝的アルゴリズム(GA)が484次元で戦略DNAの突然変異・交配・選択を行います。シグナルの重み付けは人間ではなく、自然選択が決定します。
- **Walk-Forward検証** — すべてのバックテストは70/30の学習/テスト分割とモンテカルロ・シミュレーション（1,000回反復、p < 0.05）を使用します。これは単純なインサンプル検証ではなく、機関投資家レベルの検証手法です。
- **マルチマーケット** — 暗号資産（ccxt経由、100以上の取引所）、中国A株（AKShare + BaoStock）、米国株（Yahoo Finance）。一つのエンジンですべての市場に対応します。
- **AIネイティブ** — MCPサーバーを内蔵し、Claude、Cursor、VS CodeからFinClawの相場取得、バックテスト実行、ポートフォリオ分析をネイティブに操作できます。

---

## アーキテクチャ

```
┌──────────────────────────────────────────────────────┐
│             進化エンジン (コア)                         │
│      遺伝的アルゴリズム → 突然変異 → バックテスト → 選択  │
│                                                       │
│      入力: 484ファクター × 重み = DNA                   │
│      出力: Walk-Forward検証済み戦略                     │
├──────────────────────────────────────────────────────┤
│                ファクターソース                         │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│   │テクニカル │ │センチメント│ │   DRL    │ │Davis   │ │
│   │  284     │ │  ニュース │ │Q-learning│ │Double  │ │
│   │  汎用    │ │  EN / ZH │ │ シグナル │ │ Play   │ │
│   └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
│        └─────────────┴────────────┴────────────┘      │
│   + 200の暗号資産固有ファクター                          │
│                すべて → compute() → [0, 1]             │
├──────────────────────────────────────────────────────┤
│               品質保証                                 │
│   ┌────────────┐ ┌─────────────┐ ┌────────────────┐  │
│   │   Arena    │ │   バイアス   │ │  Walk-Forward  │  │
│   │   競争     │ │    検出     │ │ + モンテカルロ  │  │
│   └────────────┘ └─────────────┘ └────────────────┘  │
├──────────────────────────────────────────────────────┤
│               実行レイヤー                              │
│   ペーパートレード → ライブトレード → 100以上の取引所      │
└──────────────────────────────────────────────────────┘
```

---

## ファクターライブラリ（484ファクター）

284の汎用ファクター + 200の暗号資産固有ファクター、カテゴリ別に整理：

| カテゴリ | 数 | 例 |
|----------|-------|---------|
| 暗号資産固有 | 200 | ファンディングレートプロキシ、セッション効果、クジラ検出、連鎖清算 |
| モメンタム | 14 | ROC、加速度、トレンド強度、クオリティ・モメンタム |
| 出来高＆フロー | 13 | OBV、スマートマネー、出来高-価格乖離、Wyckoff VSA |
| ボラティリティ | 13 | ATR、ボリンジャー・スクイーズ、レジーム検出、ボラティリティのボラティリティ |
| 平均回帰 | 12 | Zスコア、ラバーバンド、ケルトナーポジション |
| トレンドフォロー | 14 | ADX、EMAゴールデンクロス、高値切り上げ・安値切り上げ、MAファン |
| Qlib Alpha158 | 11 | KMID、KSFT、CNTD、CORD、SUMP（Microsoft Qlib互換） |
| クオリティフィルター | 11 | 収益モメンタムプロキシ、相対力、レジリエンス |
| リスク警告 | 11 | 連続損失、デッドクロス、ギャップダウン、ストップ安 |
| 天井脱出 | 10 | ディストリビューション検出、クライマックス出来高、スマートマネー退出 |
| 価格構造 | 10 | ローソク足パターン、サポート/レジスタンス、ピボットポイント |
| Davis Double Play | 8 | 売上加速、テクノロジー・モート、供給枯渇 |
| アルファ | 10 | 各種アルファファクターの実装 |
| ギャップ分析 | 8 | ギャップフィル、ギャップモメンタム、ギャップリバーサル |
| 市場幅 | 5 | 騰落指標、セクターローテーション、新高値/新安値 |
| ニュースセンチメント | 2 | EN/ZHキーワードセンチメントスコア + モメンタム |
| DRLシグナル | 2 | Q-learning買い確率 + 状態値推定 |
| ... 他多数 | 130 | ファンダメンタルプロキシ、プルバック、底値確認、レジームなど |

> **設計思想**: テクニカル、センチメント、DRL、ファンダメンタルのすべてのシグナルは`[0, 1]`を返すファクターとして統一的に表現されます。重み付けは進化エンジンが決定し、シグナル合成に人間のバイアスを持ち込みません。

---

## 進化エンジン

遺伝的アルゴリズム(GA)が最適な戦略を継続的に発見します：

1. **シード** — 多様なファクター重み構成で初期集団を生成
2. **評価** — Walk-Forward検証で各DNAをバックテスト
3. **選択** — 上位パフォーマーを保持
4. **変異** — ランダムな重み摂動、交配、ファクターの追加/削除
5. **反復** — マシン上で24時間365日稼働

```bash
# 暗号資産（主要ユースケース）
finclaw evolve --market crypto --generations 50

# 中国A株
finclaw evolve --market cn --generations 50

# カスタムパラメータ指定
finclaw evolve --market crypto --population 50 --mutation-rate 0.2 --elite 10
```

### 進化結果

| 市場 | 世代 | 年間収益率 | シャープレシオ | 最大ドローダウン |
|--------|-----------|---------------|--------|-------------|
| 中国A株 | 第89世代 | 2,756% | 6.56 | 26.5% |
| 暗号資産 | 第19世代 | 16,066% | 12.19 | 7.2% |

> ⚠️ **これらはヒストリカルデータでのインサンプル・バックテスト結果です**。実際のパフォーマンスは大幅に低くなります。Walk-Forwardアウトオブサンプル検証はデフォルトで有効 — 進化した戦略を信頼する前に必ずOOS指標を確認してください。`finclaw check-backtest`で結果を検証し、実資金を投入する前に`finclaw paper`でペーパートレードしてください。

---

## Arenaモード（過学習対策）

従来のバックテストは各戦略を個別に評価するため、過学習した戦略がヒストリカルデータでは好成績でもライブでは失敗します。FinClawの**Arenaモード**（[FinEvo](https://arxiv.org)に着想）がこの問題を解決します：

```
┌──────────────────────────────────────────┐
│         Arena: 共有マーケットシミュレーション │
│                                           │
│   DNA-1 ──┐                              │
│   DNA-2 ──┤── 同一のOHLCVデータ            │
│   DNA-3 ──┤── 同一の初期資金               │
│   DNA-4 ──┤── 混雑時にはプライスインパクト発生│
│   DNA-5 ──┘── 最終損益でランキング          │
│                                           │
│   過学習DNA → 低ランク → ペナルティ          │
└──────────────────────────────────────────┘
```

- 複数のDNA戦略が同一のシミュレーション市場で同時に取引
- **混雑ペナルティ**: 50%以上のDNA戦略が同じシグナルで買いに入ると、プライスインパクトが発動
- 孤立環境でしか機能しない過学習戦略はArenaランキングでペナルティを受ける

---

## バイアス検出

結果を信頼する前に、バックテストの一般的な落とし穴を検出します：

```bash
python -m src.evolution.bias_cli --all
```

| チェック項目 | 検出内容 |
|-------|----------------|
| **先読みバイアス** | 将来データを誤って参照しているファクター |
| **データスヌーピング** | 学習データでテストデータの3倍以上のパフォーマンスを出すDNA（過学習） |
| **生存者バイアス** | バックテスト期間中に上場廃止になった銘柄 |

---

## CLIリファレンス

FinClawは70以上のサブコマンドを搭載しています。主要なものを紹介します：

```bash
# 相場 & データ
finclaw quote AAPL              # 米国株相場
finclaw quote BTC/USDT          # 暗号資産相場 (ccxt経由)
finclaw history NVDA            # ヒストリカルデータ
finclaw download-crypto         # 暗号資産OHLCVデータのダウンロード
finclaw exchanges list          # 対応取引所を表示

# 進化 & バックテスト
finclaw evolve --market crypto  # 遺伝的アルゴリズムによる進化を実行
finclaw backtest -t AAPL        # 株式での戦略バックテスト
finclaw check-backtest          # バックテスト結果の検証

# 分析 & ツール
finclaw analyze TSLA            # テクニカル分析
finclaw screen                  # 銘柄スクリーニング
finclaw risk-report             # ポートフォリオリスクレポート
finclaw sentiment               # 市場センチメント
finclaw demo                    # 全機能デモ
finclaw doctor                  # 環境チェック

# AI機能
finclaw copilot                 # AI金融アシスタント
finclaw generate-strategy       # 自然言語 → 戦略コード
finclaw mcp serve               # AIエージェント向けMCPサーバー

# ペーパートレード
finclaw paper                   # ペーパートレードモード
finclaw paper-report            # ペーパートレード結果
```

全コマンド一覧は `finclaw --help` で確認できます。

---

## MCPサーバー（AIエージェント向け）

FinClawをClaude、Cursor、VS Code、その他MCP対応クライアント向けのツールとして公開：

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

10種類のツールを提供: `get_quote`、`get_history`、`list_exchanges`、`run_backtest`、`analyze_portfolio`、`get_indicators`、`screen_stocks`、`get_sentiment`、`compare_strategies`、`get_funding_rates`。

---

## データソース

| 市場 | ソース | APIキーは必要？ |
|--------|--------|-----------------|
| 暗号資産 | ccxt（100以上の取引所） | 不要（公開データ） |
| 米国株 | Yahoo Finance | 不要 |
| 中国A株 | AKShare + BaoStock | 不要 |
| ニュースセンチメント | CryptoCompare + AKShare | 不要 |

---

## ダッシュボード

```bash
cd dashboard && npm install && npm run dev
# http://localhost:3000 を開く
```

- リアルタイム価格（暗号資産、米国株、中国A株）
- TradingViewプロフェッショナルチャート
- リアルタイムP&L付きポートフォリオトラッカー
- フィルター＋CSVエクスポート付き銘柄スクリーナー
- AIチャットアシスタント（OpenAI、Anthropic、DeepSeek、Ollama）

---

## 検証と品質保証

- Walk-Forward検証（70/30 学習/テスト分割）
- モンテカルロ・シミュレーション（1,000回反復、p値 < 0.05）
- ブートストラップ95%信頼区間
- Arena競争（マルチDNA市場シミュレーション）
- バイアス検出（先読み、スヌーピング、生存者）
- ファクターIC/IR分析と減衰曲線
- ファクター直交行列（冗長ファクターの自動除去）
- 適合度関数における売買回転率ペナルティ
- 5,600以上の自動テスト

---

## ロードマップ

- [x] 484ファクター進化エンジン
- [x] Walk-Forward検証 + モンテカルロ
- [x] Arena競争モード
- [x] バイアス検出スイート
- [x] ニュースセンチメント + DRLファクター
- [x] Davis Double Playファクター
- [x] ペーパートレード基盤
- [x] AIエージェント向けMCPサーバー
- [ ] DEX執行（Uniswap V3 / Arbitrum）
- [ ] マルチタイムフレーム対応（1h/4h/1d）
- [ ] 価格系列向けファウンデーションモデル

---

## コントリビューション

```bash
git clone https://github.com/NeuZhou/finclaw.git
cd finclaw && pip install -e ".[dev]"
pytest
```

コントリビューションを歓迎します！ガイドラインは[CONTRIBUTING.md](CONTRIBUTING.md)をご覧ください。

**参加方法:**
- 🐛 [バグ報告](https://github.com/NeuZhou/finclaw/issues)
- 💡 [機能リクエスト](https://github.com/NeuZhou/finclaw/issues)
- 🔧 プルリクエストの送信
- 📝 ドキュメントの改善
- ⭐ お役に立てたらスターをお願いします

---

## 制約事項

FinClawは研究・教育ツールです。主な制約事項：

- **無料データソース** — 遅延、欠損、APIレート制限の影響を受けます
- **簡略化されたバックテスト** — 板情報の深さ、部分約定、マーケット・マイクロストラクチャーはモデル化していません
- **インサンプル・バイアス** — 進化した戦略がアウトオブサンプルで同様に機能するとは限りません。必ずWalk-ForwardのOOS結果を確認してください
- **まずドライラン** — 実資金を投入する前に必ずペーパートレードで戦略を検証してください

本番のトレードでは、適切なリスク管理とポジションサイジングと組み合わせてご利用ください。

---

## ライセンス

[MIT](LICENSE)

---

## Star History

<a href="https://www.star-history.com/#NeuZhou/finclaw&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date&theme=dark" />
    <img alt="Star History" src="https://api.star-history.com/svg?repos=NeuZhou/finclaw&type=Date" />
  </picture>
</a>
