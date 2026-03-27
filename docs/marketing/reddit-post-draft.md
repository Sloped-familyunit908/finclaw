# Reddit帖子草稿 — r/algotrading

## 帖子标题 (选一个)

**选项A（推荐）：**
I built an open-source engine that uses genetic algorithms to evolve crypto trading strategies — 484 factors, walk-forward validation, 127+ generations

**选项B：**
Show r/algotrading: Self-evolving crypto trading strategies via genetic algorithm (open source, Python)

**选项C：**
After 127 generations of evolution, my GA discovered trading patterns I never would have coded manually

---

## 帖子正文

Hey r/algotrading,

I've been working on an open-source project called **FinClaw** that takes a different approach to strategy development: instead of manually writing trading rules, a genetic algorithm evolves them.

**How it works:**
- Start with a population of 30 random strategy "DNAs" — each is a 484-dimensional vector of factor weights
- Each generation: backtest all strategies → select the fittest → crossbreed → mutate → repeat
- After 127 generations, the GA discovered factor combinations I never would have manually coded

**What makes it different from other bots:**
- **Self-evolving:** You don't write the strategy — natural selection does
- **Walk-forward validation:** Every strategy passes a 4-window out-of-sample test before being considered "fit." This catches overfitting before it happens
- **484 factors:** Technical, momentum, volume, sentiment, crypto-specific (funding rate proxies, liquidation cascades, session patterns, etc.)
- **Deflated Sharpe Ratio:** Corrects for multiple-testing bias (trying thousands of strategies inflates Sharpe — we account for that)

**Being honest about limitations:**
- Paper trading only right now (started 2 days ago, currently -0.2%)
- The in-sample backtests show crazy numbers (25,000% annual return) that are clearly overfit — that's exactly why I built the walk-forward system
- Solo developer + AI assistant, not a team of quants
- Still early stage (19 GitHub stars)

**Tech stack:** Python, ccxt (100+ exchanges), OKX for paper trading, Walk-Forward + Monte Carlo validation

**What I'd love feedback on:**
1. Is the walk-forward approach sufficient for anti-overfitting, or should I add more (CPCV, etc.)?
2. 484 factors seems like a lot — am I inviting the curse of dimensionality?
3. Anyone else tried GA for strategy evolution? What was your experience?

GitHub: https://github.com/NeuZhou/finclaw
MIT license, fully open source.

Happy to answer any questions about the implementation.

---

## 发帖注意事项

1. 选 "Link" 类型帖子，链接到GitHub
2. 或选 "Text" 类型帖子，贴上面的正文
3. Flair选 "Strategy" 或 "Open Source"
4. **不要在标题里加emoji**
5. **不要过度推销** — r/algotrading的人很聪明，一看到营销就downvote
6. 发完后24小时内要回复评论（很重要）
7. 如果有人质疑，诚实回答，不要防御性反应

---

## 评论回复模板（如果有人问）

**Q: "为什么不用RL/DRL?"**
A: I actually wrote about this — GA is simpler to debug, doesn't need reward shaping, and handles the multi-objective nature of trading (return vs drawdown vs consistency) more naturally. DRL agents tend to learn weird edge cases in the simulator.

**Q: "484 factors太多了"**
A: Fair point. The GA naturally prunes — in practice only ~170-200 factors have non-trivial weights after evolution. The rest converge to near-zero. It's basically built-in feature selection.

**Q: "回测结果不可信"**
A: 100% agree — that's why I built walk-forward validation. The in-sample numbers are insane and clearly overfit. The OOS validation is what actually matters, and that's what we're tracking in paper trading now.
