from __future__ import annotations

from html import escape
from pathlib import Path

from .inspector import InspectionResult


PALETTE = {
    "charcoal": "#2C2B30",
    "graphite": "#4F4F51",
    "silver": "#D6D6D6",
    "rose": "#F2C4CE",
    "coral": "#F58F7C",
}


def render_html_report(result: InspectionResult, output_path: str | Path) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(build_html(result), encoding="utf-8")


def build_html(result: InspectionResult) -> str:
    column_rows = "\n".join(
        f"""
        <tr>
          <td>{escape(profile.name)}</td>
          <td>{profile.missing}</td>
          <td>{profile.unique}</td>
          <td>{profile.invalid_dates}</td>
          <td>{profile.invalid_emails}</td>
          <td>{profile.invalid_phones}</td>
          <td>{profile.outliers}</td>
        </tr>
        """
        for profile in result.column_profiles
    )
    warning_cards = build_warning_cards(result)
    summary_items = "\n".join(f"<li>{escape(item)}</li>" for item in result.summary)
    score_offset = max(0, 314 - (314 * result.quality_score / 100))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CleanSight Data Quality Report</title>
  <style>
    :root {{
      --charcoal: {PALETTE["charcoal"]};
      --graphite: {PALETTE["graphite"]};
      --silver: {PALETTE["silver"]};
      --rose: {PALETTE["rose"]};
      --coral: {PALETTE["coral"]};
      --paper: #f5f4f2;
      --white: #ffffff;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 8% 12%, rgba(242, 196, 206, 0.24), transparent 28%),
        linear-gradient(135deg, var(--charcoal), #1f1e23 58%, #3a393f);
      color: var(--charcoal);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}

    .shell {{
      width: min(1180px, calc(100vw - 32px));
      margin: 32px auto;
      border: 1px solid rgba(255, 255, 255, 0.16);
      background: var(--paper);
      box-shadow: 0 26px 80px rgba(0, 0, 0, 0.32);
    }}

    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 24px;
      padding: 34px;
      background: var(--charcoal);
      color: var(--white);
    }}

    .eyebrow {{
      margin: 0 0 8px;
      color: var(--rose);
      font-size: 0.76rem;
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(2.4rem, 6vw, 5.8rem);
      line-height: 0.95;
      letter-spacing: 0;
    }}

    .subtitle {{
      max-width: 610px;
      margin: 16px 0 0;
      color: var(--silver);
      font-size: 1rem;
      line-height: 1.55;
    }}

    .score-ring {{
      width: 158px;
      height: 158px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      background: conic-gradient(var(--coral) {result.quality_score}%, rgba(255,255,255,0.12) 0);
      position: relative;
    }}

    .score-ring::after {{
      content: "";
      position: absolute;
      inset: 18px;
      border-radius: 50%;
      background: var(--charcoal);
    }}

    .score-ring strong {{
      position: relative;
      z-index: 1;
      color: var(--white);
      font-size: 2.4rem;
    }}

    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      padding: 18px 24px;
      background: var(--rose);
    }}

    .metric {{
      border: 1px solid rgba(44, 43, 48, 0.16);
      background: rgba(255, 255, 255, 0.62);
      padding: 16px;
    }}

    .metric span {{
      display: block;
      color: var(--graphite);
      font-size: 0.74rem;
      font-weight: 900;
      text-transform: uppercase;
    }}

    .metric strong {{
      display: block;
      margin-top: 6px;
      font-size: 2rem;
    }}

    main {{
      display: grid;
      gap: 18px;
      padding: 24px;
    }}

    .grid {{
      display: grid;
      grid-template-columns: 0.85fr 1.15fr;
      gap: 18px;
    }}

    section {{
      border: 1px solid var(--silver);
      background: var(--white);
      padding: 18px;
    }}

    h2 {{
      margin: 0 0 14px;
      font-size: 1.1rem;
    }}

    ul {{
      margin: 0;
      padding-left: 20px;
      color: var(--graphite);
      line-height: 1.7;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.84rem;
    }}

    th, td {{
      border-bottom: 1px solid #ececec;
      padding: 10px 8px;
      text-align: left;
    }}

    th {{
      color: var(--graphite);
      font-size: 0.68rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}

    .warnings {{
      display: grid;
      gap: 10px;
    }}

    .warning {{
      border-left: 5px solid var(--coral);
      background: #fff4f1;
      padding: 12px;
    }}

    .warning strong {{
      display: block;
      margin-bottom: 6px;
    }}

    footer {{
      padding: 16px 24px 24px;
      color: var(--graphite);
      font-size: 0.8rem;
    }}

    @media (max-width: 820px) {{
      header,
      .grid,
      .metrics {{
        grid-template-columns: 1fr;
      }}

      .score-ring {{
        width: 132px;
        height: 132px;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <p class="eyebrow">CleanSight Report</p>
        <h1>Data Quality<br />Inspection</h1>
        <p class="subtitle">Scanned {escape(Path(result.source).name)} for missing values, duplicates, invalid formats, outliers, and inconsistent categories.</p>
      </div>
      <div class="score-ring" aria-label="Quality score">
        <strong>{result.quality_score}</strong>
      </div>
    </header>

    <div class="metrics">
      <div class="metric"><span>Rows</span><strong>{result.row_count}</strong></div>
      <div class="metric"><span>Columns</span><strong>{result.column_count}</strong></div>
      <div class="metric"><span>Issues</span><strong>{result.issue_count}</strong></div>
      <div class="metric"><span>Duplicates</span><strong>{result.duplicate_rows}</strong></div>
    </div>

    <main>
      <div class="grid">
        <section>
          <h2>Executive Summary</h2>
          <ul>{summary_items}</ul>
        </section>
        <section>
          <h2>Category Warnings</h2>
          <div class="warnings">{warning_cards}</div>
        </section>
      </div>

      <section>
        <h2>Column Profile</h2>
        <table>
          <thead>
            <tr>
              <th>Column</th>
              <th>Missing</th>
              <th>Unique</th>
              <th>Bad Dates</th>
              <th>Bad Emails</th>
              <th>Bad Phones</th>
              <th>Outliers</th>
            </tr>
          </thead>
          <tbody>{column_rows}</tbody>
        </table>
      </section>
    </main>

    <footer>
      Generated by CleanSight. Palette inspired by charcoal, graphite, silver, rose, and coral data-report styling.
    </footer>
  </div>
</body>
</html>"""


def build_warning_cards(result: InspectionResult) -> str:
    cards: list[str] = []
    for column, warnings in result.category_warnings.items():
        for warning in warnings:
            cards.append(f'<div class="warning"><strong>{escape(column)}</strong>{escape(warning)}</div>')
    if not cards:
        return '<div class="warning"><strong>No category warnings</strong>No inconsistent category values were detected.</div>'
    return "\n".join(cards)
