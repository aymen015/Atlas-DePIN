import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from github import Auth, Github
from groq import Groq


DEFAULT_GROQ_MODEL = "qwen/qwen3.6-27b"
MAX_NEWS_AGE_DAYS = 90
MAX_CANDIDATES = 12

NEWS_QUERIES = [
    'DePIN GPU AI compute',
    '"decentralized compute" AI GPU',
    '"Akash Network" OR "io.net" OR Aethir OR Gensyn OR Nosana OR Render',
]

RELEVANCE_TERMS = (
    "depin",
    "decentralized",
    "gpu",
    "compute",
    "akash",
    "io.net",
    "render",
    "aethir",
    "gensyn",
    "nosana",
)


def clean_text(value):
    return re.sub(r"\s+", " ", (value or "")).strip()


def fetch_google_news(query):
    params = urllib.parse.urlencode(
        {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    )
    url = f"https://news.google.com/rss/search?{params}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 Atlas-DePIN-Live-Research/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        xml_bytes = response.read()

    root = ET.fromstring(xml_bytes)
    items = []

    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title"))
        link = clean_text(item.findtext("link"))
        pub_date_raw = clean_text(item.findtext("pubDate"))
        source_node = item.find("source")
        publisher = clean_text(source_node.text if source_node is not None else "")
        publisher_url = (
            clean_text(source_node.attrib.get("url"))
            if source_node is not None
            else ""
        )

        if not title or not link or not pub_date_raw:
            continue

        try:
            published = parsedate_to_datetime(pub_date_raw)
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            published = published.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue

        items.append(
            {
                "title": title,
                "link": link,
                "publisher": publisher or "Unknown source",
                "publisher_url": publisher_url,
                "published": published,
            }
        )

    return items


def get_live_candidates():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_NEWS_AGE_DAYS)
    collected = []
    seen = set()

    for query in NEWS_QUERIES:
        try:
            feed_items = fetch_google_news(query)
            print(f"RSS query returned {len(feed_items)} items: {query}")
        except Exception as exc:
            print(f"Warning: RSS query failed: {query}: {exc}")
            continue

        for item in feed_items:
            if item["published"] < cutoff:
                continue

            title_key = re.sub(r"\W+", " ", item["title"].lower()).strip()
            if title_key in seen:
                continue

            lowered = item["title"].lower()
            relevance_score = sum(
                1 for term in RELEVANCE_TERMS if term in lowered
            )
            if any(term in lowered for term in ("ai", "cloud", "infrastructure", "network")):
                relevance_score += 1

            item["relevance_score"] = relevance_score
            seen.add(title_key)
            collected.append(item)

    collected.sort(
        key=lambda item: (item.get("relevance_score", 0), item["published"]),
        reverse=True,
    )

    if len(collected) < 3:
        raise RuntimeError(
            f"Live-news verification failed: only {len(collected)} relevant items "
            f"were found in the last {MAX_NEWS_AGE_DAYS} days. README was not changed."
        )

    return collected[:MAX_CANDIDATES]


def candidate_text(items):
    lines = []
    for index, item in enumerate(items, start=1):
        date = item["published"].strftime("%Y-%m-%d")
        lines.append(f"{index}. [{date}] {item['title']} — {item['publisher']}")
    return "\n".join(lines)


def ai_select_sources(items, api_key, model):
    if not api_key:
        print("GROQ_API_KEY unavailable; using deterministic RSS fallback.")
        return None

    prompt = f"""
You are selecting live market-intelligence signals for Atlas DePIN.

Below are verified news-feed headlines from the last {MAX_NEWS_AGE_DAYS} days.
Choose exactly 3 items most relevant to decentralized AI/GPU compute.

Rules:
- Use ONLY the supplied headline, publisher, and date.
- Do not invent statistics, partnerships, funding amounts, technical details, or dates.
- Prefer substantive infrastructure, product, network, funding, or adoption developments.
- Avoid duplicate stories covering the same event.
- For each item, write one conservative "why_it_matters" sentence, max 24 words.
- Do not turn implications into factual claims.

Return JSON only:
{{"selected":[{{"source_id":1,"why_it_matters":"..."}}]}}

Candidates:
{candidate_text(items)}
"""

    try:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            reasoning_format="hidden",
            temperature=0.2,
            max_completion_tokens=700,
        )
        payload = json.loads(completion.choices[0].message.content or "{}")
        selected = payload.get("selected")

        if not isinstance(selected, list) or len(selected) != 3:
            raise ValueError("AI did not return exactly 3 selected items.")

        validated = []
        used_ids = set()

        for entry in selected:
            source_id = int(entry["source_id"])
            why = clean_text(entry.get("why_it_matters"))
            if source_id < 1 or source_id > len(items):
                raise ValueError(f"Invalid source_id: {source_id}")
            if source_id in used_ids:
                raise ValueError(f"Duplicate source_id: {source_id}")
            if not why:
                raise ValueError("Missing why_it_matters.")

            used_ids.add(source_id)
            validated.append(
                {"source_id": source_id, "why_it_matters": why}
            )

        print(f"AI selection succeeded with model: {model}")
        return validated

    except Exception as exc:
        print(f"Warning: AI enrichment unavailable; RSS fallback used: {exc}")
        return None


def fallback_why_it_matters(title):
    lowered = title.lower()

    if any(term in lowered for term in ("funding", "fundraise", "raises", "investment")):
        return "This is a live signal of capital activity around decentralized compute infrastructure."
    if any(term in lowered for term in ("launch", "mainnet", "network", "platform")):
        return "This is relevant to the availability and evolution of decentralized compute infrastructure."
    if any(term in lowered for term in ("partner", "integration", "integrates", "collaboration")):
        return "This is relevant to ecosystem integration and potential demand for decentralized compute."
    if "gpu" in lowered:
        return "This is directly relevant to GPU capacity and decentralized AI-compute market activity."

    return "This is a current market signal relevant to decentralized AI and DePIN compute."


def choose_items(items, ai_selection):
    if ai_selection:
        chosen = []
        for selection in ai_selection:
            item = dict(items[selection["source_id"] - 1])
            item["why_it_matters"] = selection["why_it_matters"]
            chosen.append(item)
        return chosen

    chosen = []
    for item in items[:3]:
        copy = dict(item)
        copy["why_it_matters"] = fallback_why_it_matters(item["title"])
        chosen.append(copy)
    return chosen


def build_market_markdown(items):
    lines = []
    for item in items:
        date = item["published"].strftime("%Y-%m-%d")
        lines.append(
            f"- **{date} — {item['publisher']}:** "
            f"[{item['title']}]({item['link']}) "
            f"**Why it matters:** {item['why_it_matters']}"
        )
    return "\n".join(lines)


def build_sources_markdown(items):
    return "\n".join(
        f"- {item['published'].strftime('%Y-%m-%d')} — "
        f"[{item['publisher']}: {item['title']}]({item['link']})"
        for item in items
    )


def run_ai_bot():
    github_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    groq_api_key = os.environ.get("GROQ_API_KEY")
    groq_model = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    if not github_token:
        raise RuntimeError("Missing GitHub token (GH_TOKEN or GITHUB_TOKEN).")

    candidates = get_live_candidates()
    print(f"Verified recent RSS candidates: {len(candidates)}")

    ai_selection = ai_select_sources(
        candidates,
        api_key=groq_api_key,
        model=groq_model,
    )
    selected_items = choose_items(candidates, ai_selection)

    market_intelligence = build_market_markdown(selected_items)
    sources_markdown = build_sources_markdown(selected_items)
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    vision_text = """# Atlas DePIN: Scaling AI Compute from Algeria to the World | Giveth

![Build Status](https://img.shields.io/badge/Status-Active-brightgreen)
![License](https://img.shields.io/badge/License-MIT-blue)
![Nodes](https://img.shields.io/badge/DePIN-Operational-orange)

## The Vision: AI for Everyone, Not the Few
Atlas DePIN is democratizing AI by providing high-performance GPU resources to the decentralized ecosystem, leveraging protocols like Akash Network and io.net. From Algeria, we are breaking the monopoly of tech giants.

## 💎 Support the Vision
Atlas-DePIN is a community-driven initiative. If you value our mission to decentralize AI compute, consider supporting our development via Giveth:

[👉 Support Atlas-DePIN on Giveth](https://giveth.io/project/atlas-depin:-scaling-ai-compute-from-algeria-to-world)

*Your contributions help us maintain nodes, upgrade hardware, and keep our AI research open to everyone.*

## The Algerian Advantage
- **Unrivaled Energy Efficiency:** Leveraging competitive energy costs to offer affordable AI compute.
- **Next-Gen Connectivity:** Powered by Medusa cable and upgraded national fiber-optics for low-latency transmission.
- **Technical Rigor:** Built on Kubernetes (K8s) and Docker for 24/7 high-availability and thermal-optimized performance.

## Technical Architecture
- **Orchestration:** Automated K8s clusters for seamless AI workload distribution.
- **Monitoring:** Real-time tracking via Prometheus/Grafana to ensure peak performance-per-watt."""

    final_readme = f"""{vision_text}

## 🚀 Live Market Intelligence
{market_intelligence}

### 🔎 Live Research Sources
{sources_markdown}

> Sources are retrieved live from Google News RSS on **{current_date} UTC**. AI only ranks and summarizes verified feed items; if AI is unavailable, the bot safely falls back to the live headlines.

---
*Updated on {current_date} via Ayman | Atlas DePIN 🇩🇿 | [LinkedIn](https://linkedin.com/in/aymen-atlas-depin) | [Twitter](https://x.com/cotex5024)*

### 🤝 How to Contribute
We welcome contributions from the community! Whether it's reporting a bug, improving documentation, or adding new DePIN insights, your help makes **Atlas-DePIN** stronger.

* **Read our guidelines:** Check out [CONTRIBUTING.md](CONTRIBUTING_TEMPLATE.md) for how to get started.
* **Have an idea?** Open a new [Issue](https://github.com/aymen015/Atlas-DePIN/issues) and let's discuss it."""

    auth = Auth.Token(github_token)
    github = Github(auth=auth)
    repo = github.get_repo("aymen015/Atlas-DePIN")

    contents = repo.get_contents("README.md")
    repo.update_file(
        contents.path,
        "feat: publish verified live DePIN market intelligence",
        final_readme,
        contents.sha,
    )
    print("Success: README updated from verified live RSS sources.")


if __name__ == "__main__":
    run_ai_bot()
