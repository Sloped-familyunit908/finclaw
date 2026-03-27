import urllib.request
import json

repos = {
    "TradingAgents": "https://api.github.com/repos/TauricResearch/TradingAgents",
    "ai-hedge-fund": "https://api.github.com/repos/virattt/ai-hedge-fund",
    "finclaw": "https://api.github.com/repos/NeuZhou/finclaw",
    "FinRL": "https://api.github.com/repos/AI4Finance-Foundation/FinRL",
    "qlib": "https://api.github.com/repos/microsoft/qlib",
    "freqtrade": "https://api.github.com/repos/freqtrade/freqtrade",
    "zipline": "https://api.github.com/repos/quantopian/zipline",
    "FinGPT": "https://api.github.com/repos/AI4Finance-Foundation/FinGPT",
    "OpenBB": "https://api.github.com/repos/OpenBB-finance/OpenBB",
    "NeMo-Guardrails": "https://api.github.com/repos/NVIDIA/NeMo-Guardrails",
    "guardrails": "https://api.github.com/repos/guardrails-ai/guardrails",
    "playwright": "https://api.github.com/repos/microsoft/playwright",
}

for name, url in repos.items():
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Python"})
        data = json.loads(urllib.request.urlopen(req).read())
        print(f"{name}: stars={data['stargazers_count']}, forks={data['forks_count']}, created={data['created_at'][:10]}")
    except Exception as e:
        print(f"{name}: ERROR - {e}")
