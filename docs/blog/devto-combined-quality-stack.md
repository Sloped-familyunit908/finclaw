---
title: "The Complete AI Agent Quality Stack: Test + Secure in One Pipeline"
published: true
tags: ai, security, testing, devops
---

Your AI agent is in production. It calls tools, reads databases, processes sensitive data, makes decisions autonomously. Thousands of requests per day, no human in the loop.

But here's the question nobody wants to answer: **do you test it?** And more importantly — **do you scan it for vulnerabilities?**

## The Problem: Two Halves of the Same Coin

Most teams treat testing and security as separate concerns. You write unit tests over here, run a security audit over there, and hope the gap between them doesn't swallow your users.

For AI agents, that gap is fatal.

An agent that passes all its behavioral tests but leaks PII through prompt injection isn't safe. An agent that's hardened against every known attack but silently calls the wrong tool isn't correct. You need both — and you need them running together, on every commit.

## AgentProbe: Does the Agent Do the Right Things?

[AgentProbe](https://github.com/NeuZhou/agentprobe) is like Playwright, but for AI agents. It lets you record, replay, and assert on agent behavior — tool calls, argument shapes, response contracts, multi-step workflows.

Write a test that says "when the user asks for a stock quote, the agent must call the `get_quote` tool with a valid ticker symbol and return a price." Run it on every PR. If the agent starts hallucinating tool calls or returning garbage, you catch it before production.

```typescript
// agentprobe test example
test('stock quote flow', async ({ agent }) => {
  const result = await agent.send('What is AAPL trading at?');
  expect(result.toolCalls).toContainEqual(
    expect.objectContaining({ name: 'get_quote', args: { symbol: 'AAPL' } })
  );
  expect(result.response).toMatch(/\$\d+/);
});
```

AgentProbe handles the hard parts — deterministic replay of non-deterministic LLM calls, snapshot-based assertions, CI integration with GitHub Actions.

## ClawGuard: Does the Agent Avoid Doing Wrong Things?

[ClawGuard](https://github.com/NeuZhou/clawguard) is an immune system for AI agents. It scans your agent code and runtime traffic for 285+ threat patterns covering:

- **Prompt injection** — direct, indirect, and multi-turn attacks
- **PII leakage** — credit cards, SSNs, emails, phone numbers slipping through outputs
- **Tool abuse** — unauthorized file access, network calls, privilege escalation
- **OWASP LLM Top 10** compliance checks

Run it as a static scanner on your source code, or plug it in as runtime middleware that blocks threats in real time.

```bash
# scan your agent source
npx @neuzhou/clawguard scan src/

# runtime protection
import { ClawGuard } from '@neuzhou/clawguard';
const guard = new ClawGuard({ block: true });
agent.use(guard.middleware());
```

## The Combined Pipeline: One YAML, Complete Coverage

Here's what a complete AI agent quality gate looks like in GitHub Actions:

```yaml
name: Agent Quality Gate
on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Test agent behavior
        uses: NeuZhou/agentprobe/.github/actions/agentprobe@master

      - name: Scan for security threats
        run: npx @neuzhou/clawguard scan src/
```

Six lines of config. Every push gets tested for correctness AND scanned for vulnerabilities. No gaps.

## Why They Work Better Together

| Concern | AgentProbe | ClawGuard |
|---|---|---|
| Does the agent call the right tools? | ✅ | — |
| Does the agent return correct data? | ✅ | — |
| Is the agent vulnerable to injection? | — | ✅ |
| Does the agent leak sensitive data? | — | ✅ |
| Does the agent behave correctly AND securely? | ✅ + ✅ | |

Testing without security is naïve. Security without testing is blind. Together, they're a complete quality stack for AI agents.

## Get Started

Both tools are open source and free to use:

- **AgentProbe**: [github.com/NeuZhou/agentprobe](https://github.com/NeuZhou/agentprobe) — test, record, replay agent behaviors
- **ClawGuard**: [github.com/NeuZhou/clawguard](https://github.com/NeuZhou/clawguard) — 285+ threat patterns, PII sanitizer, OWASP compliance

Add both to your CI pipeline today. Your agents — and your users — will thank you.
