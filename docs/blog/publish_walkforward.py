"""Publish walk-forward validation article to Dev.to using urllib."""
import json
import urllib.request
import urllib.error

API_KEY = "Gk4viv7m2hDno6vwBkRYRN7e"

# Read the article markdown
with open(r"C:\Users\kazhou\.openclaw\workspace\finclaw\docs\blog\walk-forward-article.md", "r", encoding="utf-8") as f:
    body_markdown = f.read()

article_data = {
    "article": {
        "title": "Your Backtest Is Lying to You — Walk-Forward Validation Catches Overfitting",
        "published": True,
        "body_markdown": body_markdown,
        "tags": ["python", "machinelearning", "trading", "ai"],
        "series": "Building finclaw: AI-Native Quant Engine",
        "canonical_url": None,
        "main_image": "https://raw.githubusercontent.com/NeuZhou/finclaw/master/assets/cover-127-generations.png",
    }
}

payload = json.dumps(article_data).encode("utf-8")

req = urllib.request.Request(
    "https://dev.to/api/articles",
    data=payload,
    method="POST",
    headers={
        "Content-Type": "application/json",
        "api-key": API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    },
)

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print(f"SUCCESS! Article published.")
        print(f"  ID:  {result.get('id')}")
        print(f"  URL: {result.get('url')}")
        print(f"  Slug: {result.get('slug')}")
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"HTTP Error {e.code}: {e.reason}")
    print(f"Response: {body}")
except Exception as e:
    print(f"Error: {e}")
