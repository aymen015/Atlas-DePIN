import os
import re
from datetime import datetime, timezone

from groq import Groq
from github import Auth, Github


DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
MIN_LIVE_SOURCES = 3


def _as_dict(value):
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {}


def extract_search_sources(message):
    """Extract verified URLs returned by Groq's executed web-search tool."""
    sources = []
    seen_urls = set()

    for tool in getattr(message, "executed_tools", None) or []:
        tool_data = _as_dict(tool)

        search_results = tool_data.get("search_results")
        if search_results is None:
            search_results = getattr(tool, "search_results", None)

        if hasattr(search_results, "model_dump"):
            search_results = search_results.model_dump()

        if isinstance(search_results, dict):
            results = search_results.get("results", [])
        elif isinstance(search_results, list):
            results = search_results
        else:
            results = []

        for result in results:
            result_data = _as_dict(result) if not isinstance(result, dict) else result
            url = (result_data.get("url") or "").strip()
            title = (result_data.get("title") or url).strip()
            if url and url not in seen_urls:
                sources.append({"title": title, "url": url})
                seen_urls.add(url)

        # Compatibility fallback for SDK/API response shapes that expose
        # raw tool output instead of structured search_results.
        output = tool_data.get("output") or getattr(tool, "output", "") or ""
        if isinstance(output, str):
            for url in re.findall(r"https?://[^\s)\]}>\"']+", output):
                url = url.rstrip(".,;:")
                if url not in seen_urls:
                    sources.append({"title": url, "url": url})
                    seen_urls.add(url)

    return sources


def build_sources_markdown(sources, limit=6):
    lines = []
    for source in sources[:limit]:
        safe_title = source["title"].replace("[", "").replace("]", "")
        lines.append(f"- [{safe_title}]({source['url']})")
    return "\n".join(lines)


def run_ai_bot():
    groq_api_key = os.environ.get("GROQ_API_KEY")
    github_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    groq_model = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    if not groq_api_key:
        raise RuntimeError("Missing GROQ_API_KEY environment variable.")
    if not github_token:
        raise RuntimeError("Missing GitHub token (GH_TOKEN or GITHUB_TOKEN).")

    client = Groq(api_key=groq_api_key)

    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = f"""
Search the live web for the 3 most important developments in decentralized AI/GPU compute or DePIN infrastructure as of {current_date} UTC.

Prefer the last 7 days; expand to 30 days only if needed.
Focus on projects such as Akash, io.net, Render, Aethir, Gensyn, Nosana, or comparable decentralized compute networks.
Use only claims supported by search results. Never invent numbers, dates, partnerships, or announcements.

Return exactly 3 concise Markdown bullets, under 160 words total.
Each bullet: date when available, topic/project, what changed, and why it matters.
No heading, intro, conclusion, or separate source list.
"""
    print(f"Using Groq model with browser search: {groq_model}")
    completion = client.chat.completions.create(
        model=groq_model,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "browser_search"}],
    )

    message = completion.choices[0].message
    market_intelligence = (message.content or "").strip()
    sources = extract_search_sources(message)

    if not market_intelligence:
        raise RuntimeError("Groq returned no market intelligence; README was not changed.")

    if len(sources) < MIN_LIVE_SOURCES:
        raise RuntimeError(
            f"Live research verification failed: only {len(sources)} unique web sources "
            f"were returned; need at least {MIN_LIVE_SOURCES}. README was not changed."
        )

    print(f"Verified live web sources: {len(sources)}")
    sources_markdown = build_sources_markdown(sources)

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

> Research retrieved live from the web on **{current_date} UTC**. If live-source verification fails, the bot leaves the previous README unchanged.

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
    print("Success: README updated from verified live web research.")


if __name__ == "__main__":
    run_ai_bot()
