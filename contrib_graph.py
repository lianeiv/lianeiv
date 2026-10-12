#!/usr/bin/env python3
"""Gera assets/contribution-graph.svg (gráfico de contribuições dos últimos N dias).

Roda dentro do GitHub Actions usando o GITHUB_TOKEN. Só usa a biblioteca padrão.
Uso:  python contrib_graph.py            (precisa de GITHUB_TOKEN e GH_USER)
      python contrib_graph.py --demo     (dados fictícios, só para testar o visual)
"""
import json, os, sys, random
import urllib.request
from datetime import date, timedelta

USER = os.environ.get("GH_USER", "lianeiv")
DAYS = int(os.environ.get("GRAPH_DAYS", "31"))
OUT = os.environ.get("GRAPH_OUT", "assets/contribution-graph.svg")

# Paleta rosa
BG, BORDER = "#0d1117", "#30363d"
TXT, MUTED = "#C9D1D9", "#8B949E"
LINE, AREA, TITLE = "#E8A0C8", "#B83E86", "#DA70D6"

QUERY = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from,to:$to){
      contributionCalendar{ weeks{ contributionDays{ date contributionCount } } }
    }
  }
}"""


def fetch(days):
    token = os.environ["GITHUB_TOKEN"]
    end = date.today()
    start = end - timedelta(days=days - 1)
    body = json.dumps({
        "query": QUERY,
        "variables": {"login": USER, "from": f"{start}T00:00:00Z", "to": f"{end}T23:59:59Z"},
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"Erro na API do GitHub: {data['errors']}")
    counts = {}
    for w in data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for d in w["contributionDays"]:
            counts[d["date"]] = d["contributionCount"]
    return [(start + timedelta(days=i), counts.get((start + timedelta(days=i)).isoformat(), 0))
            for i in range(days)]


def demo(days):
    random.seed(7)
    end = date.today()
    return [(end - timedelta(days=days - 1 - i), random.choice([0, 0, 1, 2, 3, 5, 8, 12])) for i in range(days)]


def nice_max(v):
    for step in (4, 8, 12, 16, 20, 40, 80, 120, 200, 400, 800):
        if v <= step:
            return step
    return ((int(v) + 3) // 4) * 4


def render(series):
    W, H = 900, 300
    L, R, T, B = 56, 24, 56, 48
    pw, ph = W - L - R, H - T - B
    ymax = nice_max(max(c for _, c in series) or 1)
    n = len(series)
    xs = [L + (pw * i / (n - 1) if n > 1 else 0) for i in range(n)]
    ys = [T + ph - (c / ymax) * ph for _, c in series]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"{xs[0]:.1f},{T+ph} {pts} {xs[-1]:.1f},{T+ph}"
    total = sum(c for _, c in series)

    g = []
    for k in range(5):  # grade horizontal + rótulos do eixo Y
        v = ymax * k / 4
        y = T + ph - ph * k / 4
        g.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="{BORDER}" stroke-dasharray="3 4"/>')
        g.append(f'<text x="{L-10}" y="{y+4:.1f}" text-anchor="end" fill="{MUTED}" font-size="11">{v:g}</text>')
    step = max(1, n // 7)
    for i in range(0, n, step):  # rótulos do eixo X (dia/mês)
        g.append(f'<text x="{xs[i]:.1f}" y="{T+ph+20}" text-anchor="middle" fill="{MUTED}" font-size="11">{series[i][0].strftime("%d/%m")}</text>')
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#fff" stroke="{LINE}" stroke-width="1.5"/>' for x, y in zip(xs, ys))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Gráfico de contribuições de {USER} nos últimos {n} dias">
  <style>text{{font-family:'Segoe UI',Ubuntu,Arial,sans-serif}}</style>
  <defs>
    <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{AREA}" stop-opacity=".55"/>
      <stop offset="1" stop-color="{AREA}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
  <text x="{W/2}" y="28" text-anchor="middle" fill="{TITLE}" font-size="16" font-weight="700">Gráfico de contribuições · últimos {n} dias</text>
  <text x="{W/2}" y="46" text-anchor="middle" fill="{MUTED}" font-size="11">{total} contribuições</text>
  {chr(10).join("  " + s for s in g)}
  <polygon points="{area}" fill="url(#fill)"/>
  <polyline points="{pts}" fill="none" stroke="{LINE}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
  {dots}
</svg>
'''


if __name__ == "__main__":
    series = demo(DAYS) if "--demo" in sys.argv else fetch(DAYS)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(series))
    print(f"OK: {OUT} ({sum(c for _, c in series)} contribuições em {len(series)} dias)")