"""PDF Report Generator — pure Python, HTML-based print-friendly reports.

Falls back to enhanced HTML that prints well as PDF via browser print dialog.
If *weasyprint* or *reportlab* are installed they are used, otherwise plain HTML.
"""

from __future__ import annotations

import html as _html
import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ReportSection:
    title: str
    content: str  # HTML fragment
    order: int = 0


class PDFReportGenerator:
    """Generate print-optimised HTML reports (or PDF when libs available)."""

    def __init__(self, title: str = "FinClaw Report", author: str = "FinClaw"):
        self.title = title
        self.author = author
        self._sections: List[ReportSection] = []

    def add_section(self, title: str, content: str, order: int = 0) -> None:
        self._sections.append(ReportSection(title, content, order))

    def add_key_metrics(self, metrics: Dict[str, Any]) -> None:
        rows = "".join(
            f"<tr><td><strong>{_html.escape(str(k))}</strong></td><td>{_html.escape(str(v))}</td></tr>"
            for k, v in metrics.items()
        )
        self.add_section("Key Metrics", f"<table>{rows}</table>")

    def add_text(self, title: str, text: str) -> None:
        self.add_section(title, f"<p>{_html.escape(text)}</p>")

    def add_table(self, title: str, headers: list, rows: list) -> None:
        hdr = "".join(f"<th>{_html.escape(str(h))}</th>" for h in headers)
        body = ""
        for row in rows:
            body += "<tr>" + "".join(f"<td>{_html.escape(str(c))}</td>" for c in row) + "</tr>"
        self.add_section(title, f"<table><thead><tr>{hdr}</tr></thead><tbody>{body}</tbody></table>")

    # ------------------------------------------------------------------

    def _build_html(self) -> str:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sections_html = ""
        for s in sorted(self._sections, key=lambda s: s.order):
            sections_html += f'<div class="section"><h2>{_html.escape(s.title)}</h2>{s.content}</div>\n'
        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{_html.escape(self.title)}</title>
<style>
@page{{margin:2cm}}
*{{box-sizing:border-box}}
body{{font-family:'Segoe UI',Helvetica,Arial,sans-serif;color:#1e293b;max-width:800px;margin:0 auto;padding:40px 24px;line-height:1.6}}
h1{{border-bottom:3px solid #2563eb;padding-bottom:8px;margin-bottom:4px}}
.meta{{color:#64748b;font-size:13px;margin-bottom:24px}}
.section{{margin-bottom:28px;page-break-inside:avoid}}
h2{{color:#2563eb;font-size:18px;margin-bottom:8px}}
table{{width:100%;border-collapse:collapse;margin-top:8px}}
th,td{{padding:6px 10px;border:1px solid #cbd5e1;text-align:left;font-size:13px}}
th{{background:#f1f5f9;font-weight:600}}
p{{margin:6px 0}}
@media print{{body{{padding:0}}}}
</style></head><body>
<h1>{_html.escape(self.title)}</h1>
<div class="meta">Generated {now} by {_html.escape(self.author)}</div>
{sections_html}
</body></html>"""

    def generate(self, output_path: str) -> str:
        """Write report. Returns path written (HTML or PDF)."""
        html_content = self._build_html()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Try weasyprint → reportlab → fallback to HTML
        if out.suffix.lower() == ".pdf":
            try:
                import weasyprint  # type: ignore
                weasyprint.HTML(string=html_content).write_pdf(str(out))
                return str(out)
            except ImportError:
                pass
            # Fallback: write as HTML with .html extension
            out = out.with_suffix(".html")

        out.write_text(html_content, encoding="utf-8")
        return str(out)
