import urllib.request
import json
import time

repos = {
    "OpenBB": "https://api.github.com/repos/OpenBB-finance/OpenBB",
    "NeMo-Guardrails": "https://api.github.com/repos/NVIDIA/NeMo-Guardrails",
    "guardrails-ai": "https://api.github.com/repos/guardrails-ai/guardrails",
    "playwright": "https://api.github.com/repos/microsoft/playwright",
    "AgentOps": "https://api.github.com/repos/AgentOps-AI/agentops",
    "agenteval": "https://api.github.com/repos/aws/agenteval",
}

for name, url in repos.items():
    try:
        time.sleep(1)
        req = urllib.request.Request(url, headers={"User-Agent": "Python"})
        data = json.loads(urllib.request.urlopen(req).read())
        print(f"{name}: stars={data['stargazers_count']}, forks={data['forks_count']}, created={data['created_at'][:10]}")
    except Exception as e:
        print(f"{name}: ERROR - {e}")
