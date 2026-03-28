# GitHub Trending — Research & Launch Plan

**Date:** 2026-03-27
**Repos:** finclaw (Python) · agentprobe (TypeScript) · clawguard (TypeScript)
**Current Stars:** finclaw=19 · agentprobe=1 · clawguard=1

---

## Part 1: How GitHub Trending Works

### Algorithm Mechanics

GitHub Trending is based on **star velocity** (rate of new stars), NOT absolute star count. Key facts:

1. **Star velocity is king** — A repo with 10 stars going to 50 in a day will trend over a repo with 50,000 stars getting 20/day
2. **Time windows:** Daily (24h), Weekly (7 days), Monthly (30 days)
3. **Language-filtered lists are easier** — Competing in "Python" or "TypeScript" is significantly easier than "All languages"
4. **New repos get a boost** — GitHub appears to favor repos less than ~30 days old for trending, rewarding novelty
5. **Stars from unique, aged accounts matter** — Suspected bot/spam filtering discounts stars from brand-new accounts or coordinated patterns
6. **Forks and engagement are secondary signals** — Stars dominate, but forks/watchers may act as tiebreakers

### Current Trending Thresholds (2026-03-27, Live Data)

#### Python — Daily Trending
| Position | Repo | Stars Today | Total Stars |
|----------|------|-------------|-------------|
| #1 | mvanhorn/last30days-skill | **2,824** | 11,925 |
| #2 | bytedance/deer-flow | **2,126** | 49,766 |
| #3 | datalab-to/chandra | **913** | 6,736 |
| #4 | alirezarezvani/claude-skills | **240** | 7,343 |
| #5 | SakanaAI/AI-Scientist-v2 | **125** | 2,686 |
| #6 | trustgraph-ai/trustgraph | **109** | 1,663 |
| #7 | dreammis/social-auto-upload | **81** | 9,378 |
| #8 | SolaceLabs/solace-agent-mesh | **46** | 2,579 |
| #9 | trailofbits/skills | **31** | 4,005 |
| #10 | databricks-solutions/ai-dev-kit | **15** | 1,055 |
| #11 | ruc-datalab/DeepAnalyze | **12** | 3,888 |

**Minimum to appear on Python Daily: ~12-15 stars/day**
**Comfortable target: 50-100 stars/day to be mid-page**
**Top of page: 200+ stars/day**

#### TypeScript — Daily Trending
| Position | Repo | Stars Today | Total Stars |
|----------|------|-------------|-------------|
| #1 | Yeachan-Heo/oh-my-claudecode | **1,402** | 13,510 |
| #2 | virattt/dexter | **673** | 19,441 |
| #3 | twentyhq/twenty | **661** | 41,738 |
| #4 | letta-ai/claude-subconscious | **446** | 1,834 |
| #5 | Fission-AI/OpenSpec | **339** | 34,846 |
| #6 | langfuse/langfuse | **78** | 23,885 |
| #7 | microsoft/playwright-mcp | **78** | 29,831 |
| #8 | steipete/oracle | **67** | 1,759 |
| #9 | nrslib/takt | **20** | 860 |
| #10 | backstage/backstage | **15** | 32,946 |
| #11 | microsoft/fluentui | **7** | 19,896 |

**Minimum to appear on TypeScript Daily: ~7-20 stars/day**
**Comfortable target: 50-80 stars/day**

#### Weekly Trending (higher sustained effort needed)
- Python weekly bottom: ~495 stars/week (~70/day sustained)
- TypeScript weekly bottom: ~398 stars/week (~57/day sustained)
- Python weekly top: 16,126 stars/week (bytedance/deer-flow)

### Key Insight: Language Category Strategy

**TypeScript daily** has a lower floor (7 stars/day for bottom) than Python (12 stars/day). However, the AI/agent wave is currently massively inflating Python numbers.

**Recommendation:** Target **TypeScript daily** for clawguard/agentprobe first (lower threshold), then **Python daily** for finclaw.

---

## Part 2: What Needs to Change on Our Repos

### 2A. finclaw (Python) — Currently 19 Stars

**Description optimization:**
- Current: "AI-native quantitative finance engine. Quotes, backtesting, paper trading, strategy evolution, and MCP server."
- **Recommended:** "🧬 Self-evolving trading strategies — genetic algorithms discover what humans can't. 484 factors, walk-forward validation, MCP server. Zero API keys to start."
- Why: More specific, hooks curiosity, mentions MCP (hot topic)

**Topics to add/optimize:**
```
quantitative-finance, genetic-algorithm, trading, backtesting, 
mcp-server, ai-agent, paper-trading, crypto, stocks, 
algorithmic-trading, evolution, factor-investing, strategy
```

**README changes needed:**
- ✅ Already excellent — has demo GIFs, comparison table, quick start
- Add a **"⭐ Star this repo"** badge/CTA at the top
- Add **"Made with Claude"** or similar AI-built badge (currently hot on GitHub)
- Consider adding a **GIF/video** of `finclaw demo` output at the very top (before any text)
- Add social proof: "As seen on [HackerNews/Dev.to]" once posted

### 2B. clawguard (TypeScript) — Currently 1 Star

**Description optimization:**
- Current: "AI Agent Immune System. 285+ threat patterns, PII sanitizer, prompt injection detection, OWASP compliance."
- **Recommended:** "🛡️ The missing security layer for AI agents. 285+ threat patterns, MCP firewall, PII sanitizer — because Guardrails AI only protects the LLM, not the agent."
- Why: Positions against known competitor, uses "missing X for Y" formula

**Topics to add:**
```
ai-security, agent-security, prompt-injection, mcp-firewall,
pii-detection, guardrails, owasp, ai-agent, cybersecurity,
llm-security, claude-code, typescript, security-tools
```

**README changes needed:**
- ✅ Already strong with architecture diagrams and comparison table
- Add a **one-liner install + scan demo** at the very top (before the hero image)
- Add animated terminal GIF showing a scan in action
- Ensure the ClawGuard ↔ AgentProbe integration callout is prominent

### 2C. agentprobe (TypeScript) — Currently 1 Star

**Description optimization:**
- Current: "Playwright for AI Agents. Test, record, and replay agent behaviors with behavioral contracts."
- **Recommended:** "🎭 Playwright for AI Agents — test what your agent DOES, not just what it says. Tool call assertions, chaos testing, contract testing. Works with any LLM."
- Why: "Playwright for X" is a proven naming hook; emphasizes unique differentiation

**Topics to add:**
```
ai-testing, agent-testing, playwright, test-framework, 
chaos-testing, tool-testing, llm-testing, ai-agent,
behavioral-testing, typescript, contract-testing, ci-cd
```

**README changes needed:**
- ✅ Already strong with comparison table and YAML examples
- Add **quick video/GIF** of running tests at the top
- Make the "Playwright for AI Agents" tagline more visually prominent
- Add a "Works with Claude Code, Cursor, OpenAI, etc." compatibility section

### 2D. General Repo Hygiene for All Three

- [ ] **Social preview image** (custom og:image) — 1280×640px, branded, clear what it does
- [ ] **License badge** visible in README
- [ ] **CI badges** (green builds) visible
- [ ] **Contributing guide** (CONTRIBUTING.md) — signals healthy project
- [ ] **Good first issues** labeled — signals welcoming community
- [ ] **Discussions** tab enabled — gives visitors a reason to engage
- [ ] **Release/tag** — have at least v0.1.0 tagged
- [ ] **GitHub Pages or demo link** — if possible, a live demo

---

## Part 3: Multi-Platform Launch Plan

### Strategic Premise

We need **50-100 stars in 24 hours** to hit TypeScript daily trending (for clawguard/agentprobe), or **~100+ stars** for Python daily (finclaw). 

The flywheel effect is critical: once you appear on Trending, you get organic stars from Trending browsers, which keeps you on Trending longer.

### Launch Sequencing — "The 48-Hour Blitz"

**Pick ONE repo to launch first.** Don't split attention. 

**Recommendation: Launch agentprobe first.**
- Why: "Playwright for AI Agents" is the most meme-able/shareable concept
- TypeScript trending has a lower threshold
- The AI testing space is hot but less crowded than security
- It cross-promotes clawguard (integration callout)

#### Phase 0: Pre-Launch (Days -3 to -1)

1. **Polish the repo** (all items from Part 2)
2. **Create demo content:**
   - 60-second screen recording GIF for README
   - 2-minute YouTube demo video
   - Write the HN Show HN post draft
   - Write the Reddit posts draft
   - Write the Dev.to article
   - Write the Twitter/X thread
   - Prepare a Chinese version for V2EX / 掘金 / CSDN
3. **Seed signal:**
   - Star from personal accounts / friends (5-10 stars to avoid "0 stars" stigma)
   - Open 3-5 issues with "good first issue" labels
   - Have 1-2 PRs ready to merge during launch day (shows activity)

#### Phase 1: Launch Day (T+0) — Pick a TUESDAY or WEDNESDAY

**Why Tue/Wed:** GitHub Trending resets behavior around UTC midnight. Weekday launches get more developer eyeballs. Avoid Friday (people stop working) and Monday (email catch-up).

**Timeline (all times in UTC, add 8h for UTC+8):**

| Time (UTC) | Time (UTC+8) | Action | Expected Stars |
|------------|--------------|--------|----------------|
| 05:00 | 13:00 | Post on **V2EX** (Creative / 分享发现) | 5-10 |
| 05:30 | 13:30 | Post on **掘金 (Juejin)** article | 5-10 |
| 06:00 | 14:00 | Post on **CSDN** blog | 3-5 |
| 08:00 | 16:00 | Publish **Dev.to** article | 10-20 |
| 12:00 | 20:00 | **Hacker News** — Show HN post | 20-100+ 🎯 |
| 12:30 | 20:30 | **Twitter/X** thread (English) | 15-50 |
| 13:00 | 21:00 | **Reddit** r/programming + r/artificial | 10-30 |
| 13:30 | 21:30 | **Reddit** r/MachineLearning (if finclaw) | 5-15 |
| 14:00 | 22:00 | **LinkedIn** post | 5-10 |
| 14:00 | 22:00 | Post in relevant **Discord servers** (AI, TypeScript, testing communities) | 5-15 |

**HN is the single highest-leverage platform.** A front-page HN post can deliver 100-500+ stars in hours. Time it for ~12:00 UTC (US East Coast morning).

#### Phase 2: Sustain (T+12 to T+48)

| Time | Action | Purpose |
|------|--------|---------|
| T+12h | Engage with ALL comments on HN/Reddit/Twitter | Keep engagement up, bumps HN ranking |
| T+18h | Post follow-up tweet with metrics/reactions | "Wow, 50 stars in 12 hours" social proof |
| T+24h | Cross-post to **微信公众号** / WeChat groups | Chinese developer audience |
| T+24h | Share in **Telegram** AI/dev channels | Global dev audience |
| T+36h | Post **"Day 1 of building X in public"** thread | Build-in-public narrative |
| T+48h | If on Trending, screenshot it → tweet/post | Social proof flywheel |

#### Phase 3: Cascade (T+48 to T+7d)

Once one repo is on Trending:
- Launch repo #2 (clawguard) — cross-reference from agentprobe
- The ecosystem story ("test + secure your agents") is more compelling than solo repos
- Consider a blog post: "Building an AI Agent Security Ecosystem"

### Expected Star Conversion by Platform

| Platform | Reach | Click Rate | Star Rate | Expected Stars | Notes |
|----------|-------|------------|-----------|----------------|-------|
| Hacker News (front page) | 50,000+ views | 5-10% | 2-5% | **50-250** | Single most important platform |
| Hacker News (page 2-3) | 5,000 views | 3% | 2% | **3-10** | Minimum realistic |
| Reddit r/programming | 20,000 views | 3% | 1% | **6-20** | |
| Reddit r/artificial | 10,000 views | 5% | 2% | **10-20** | AI audience is more engaged |
| Twitter/X (viral thread) | 50,000 imp | 2% | 1% | **10-50** | |
| Twitter/X (normal) | 5,000 imp | 2% | 1% | **1-5** | |
| Dev.to article | 5,000 reads | 3% | 1% | **1-5** | Slow burn, good for SEO |
| V2EX | 10,000 views | 3% | 1% | **3-10** | Chinese dev audience |
| 掘金 | 10,000 views | 2% | 1% | **2-5** | Chinese dev audience |
| Discord communities | 2,000 views | 5% | 2% | **2-5** | |
| LinkedIn | 5,000 views | 1% | 0.5% | **0-3** | Low conversion but good for network |
| GitHub Trending (if achieved) | 100,000+ /day | N/A | N/A | **100-500/day** | 🎯 The goal — organic flywheel |

**Conservative total: ~50-100 stars in 24h**
**Optimistic (HN front page): ~200-500 stars in 24h**

### Platform-Specific Content Strategy

#### Hacker News — "Show HN" Post

**Title formula that works:**
```
Show HN: AgentProbe – Playwright for AI Agents (test what your agent does, not says)
```
- Short, curiosity-driving
- "Playwright for X" is instantly understood
- Parenthetical adds the hook

**Comment strategy:**
- First comment = detailed "what/why/how" (3-4 paragraphs)
- Mention the technical challenge honestly
- Don't be salesy — HN hates promotion
- Respond to EVERY comment within 1 hour

**⚠️ HN Karma Requirement:** Current karma is 7. Need at least 10+ for Show HN to not get flagged. **Action: Comment regularly on HN for the next week before launch.**

#### Twitter/X Thread Format
```
🎭 I built "Playwright for AI Agents"

Your agent picks tools, handles failures, generates responses autonomously.

But you test... none of that.

AgentProbe fixes this → [link]

Thread 🧵👇
```
Then 5-7 tweets showing:
1. The problem (agents are untested)
2. YAML test example
3. Chaos testing example
4. Security scanning
5. Demo GIF
6. Comparison table
7. CTA to star

#### Reddit Post
- r/programming: Technical angle, show code
- r/artificial: "I built a testing framework for AI agents"
- r/ChatGPT or r/ClaudeAI: "How to test your AI agent pipelines"
- r/LocalLLaMA: If applicable

#### Dev.to Article
Long-form (1500-2000 words):
- "Why Nobody Tests Their AI Agents (And How to Start)"
- Include code examples, screenshots
- Cross-link to GitHub

---

## Part 4: HN Karma Building Plan (Pre-Launch)

Current karma: 7. Need: 30+ (ideally 50+) for credible Show HN.

**Daily plan for next 2 weeks:**

| Day | Action | Target Karma |
|-----|--------|-------------|
| Day 1-3 | Comment on 2-3 front-page stories/day about AI/testing | +5-10 |
| Day 4-7 | Share thoughtful takes on AI agent security topics | +10-15 |
| Day 8-10 | Comment on Show HN posts (solidarity & good feedback) | +5-10 |
| Day 11-14 | Submit 1-2 interesting links (not your own) | +5 |
| **Day 14** | **Launch Show HN** | 30-50 karma |

**Comment quality rules (already in TOOLS.md, respect them!):**
- One point per comment, keep it short
- Personal experience: "I ran into this when..."
- No AI-sounding language
- No emoji, no exclamation marks

---

## Part 5: Priority Order & Timeline

### Recommended Sequence

1. **Week 1 (Now → Apr 3):** Repo polish + HN karma building
   - Apply all README/topic/description changes
   - Create demo GIFs and video content
   - Comment daily on HN to build karma to 30+
   - Draft all launch posts

2. **Week 2 (Apr 3-4):** Launch agentprobe (Tuesday/Wednesday)
   - Execute the 48-hour blitz plan
   - Target: TypeScript daily trending

3. **Week 2-3 (Apr 5-10):** Sustain + launch clawguard
   - If agentprobe trended, ride the wave
   - Launch clawguard with cross-reference
   - "The ecosystem" narrative

4. **Week 3-4 (Apr 10-17):** Launch finclaw
   - Different audience (quantitative finance)
   - Target: Python daily trending
   - Content angle: "AI discovers trading strategies you never would"

### Success Metrics

| Metric | Minimum | Target | Stretch |
|--------|---------|--------|---------|
| Stars in 24h (per repo) | 50 | 150 | 500+ |
| Appear on Trending (language) | 1 repo | 2 repos | All 3 |
| HN Show HN upvotes | 20 | 100 | 300+ |
| Total stars across all repos (30 days) | 200 | 1,000 | 5,000 |

---

## Part 6: Anti-Patterns to Avoid

1. **Don't buy stars or use star bots** — GitHub detects and penalizes this; repos have been removed
2. **Don't launch all 3 at once** — splits attention, dilutes each launch
3. **Don't launch on Friday/weekend** — lower developer traffic
4. **Don't neglect engagement** — responding to comments/issues is what keeps momentum
5. **Don't have an empty repo** — needs real code, real tests, real docs before launch
6. **Don't spam multiple subreddits simultaneously** — Reddit auto-flags cross-posting
7. **Don't use clickbait descriptions** — developers see through it, hurts trust

---

## Appendix: Trending Flywheel Dynamics

```
Post on HN/Reddit/Twitter
        ↓
   Stars spike (50-200)
        ↓
   Hit Trending page
        ↓
   Organic discovery (100-500/day)
        ↓
   More stars + forks
        ↓
   Newsletter/blog pickups (e.g., console.dev, TLDR, etc.)
        ↓
   Sustained stars for 3-7 days
        ↓
   Weekly/Monthly trending
```

The key insight: **You need to generate an initial spike large enough in a short enough window to break onto the Trending page. After that, the Trending page does the work for you.**

For our repos, the minimum viable spike is:
- **TypeScript daily: ~20-50 stars in 24 hours** (low-competition days)
- **Python daily: ~50-100 stars in 24 hours** (more competitive)

This is achievable with a well-executed HN + Reddit + Twitter combo on the same day.
