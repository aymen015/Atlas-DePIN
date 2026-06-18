import os
import random
from groq import Groq
from github import Github, Auth
from datetime import datetime

def run_ai_bot():
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GH_TOKEN = os.environ.get("GH_TOKEN")

    if not GROQ_API_KEY or not GH_TOKEN:
        print("Error: Missing Environment Variables.")
        return

    # 1. تحليل ذكاء السوق
    client = Groq(api_key=GROQ_API_KEY)
    prompt = """
    Act as a DePIN analyst. Provide 3 short, technical insights on current 
    trends in decentralized AI compute (e.g., GPU demand, DePIN protocols). 
    Keep it extremely concise (under 200 words total).
    """
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile"
    )
    market_intelligence = chat_completion.choices[0].message.content

    # 2. نص المشروع الثابت
    vision_text = """
# Atlas DePIN: Scaling AI Compute from Algeria to the World | Giveth

![Build Status](https://img.shields.io/badge/Status-Active-brightgreen)
![License](https://img.shields.io/badge/License-MIT-blue)
![Nodes](https://img.shields.io/badge/DePIN-Operational-orange)

## The Vision: AI for Everyone, Not the Few
Atlas DePIN is democratizing AI by providing high-performance GPU resources to the decentralized ecosystem, leveraging protocols like Akash Network and io.net. From Algeria, we are breaking the monopoly of tech giants.

## 💎 Support the Vision
Atlas-DePIN is a community-driven initiative. If you value our mission to decentralize AI compute, consider supporting our development via Giveth:

[👉 Support Atlas-DePIN on Giveth](https://giveth.io/project/atlas-depin)

*Your contributions help us maintain nodes, upgrade hardware, and keep our AI research open to everyone.*

## The Algerian Advantage
- **Unrivaled Energy Efficiency:** Leveraging competitive energy costs to offer affordable AI compute.
- **Next-Gen Connectivity:** Powered by Medusa cable and upgraded national fiber-optics for low-latency transmission.
- **Technical Rigor:** Built on Kubernetes (K8s) and Docker for 24/7 high-availability and thermal-optimized performance.

## Technical Architecture
- **Orchestration:** Automated K8s clusters for seamless AI workload distribution.
- **Monitoring:** Real-time tracking via Prometheus/Grafana to ensure peak performance-per-watt.
"""

    # 3. إعداد المحتوى الديناميكي والعشوائي
    fun_facts = [
        "Did you know? DePIN can reduce infrastructure costs by up to 40%.",
        "The future of AI compute is decentralized, and it's happening now.",
        "Energy efficiency is the heartbeat of sustainable AI."
    ]
    random_fact = random.choice(fun_facts)
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    final_readme = f"""{vision_text}

## 🚀 Live Market Intelligence
{market_intelligence}

> *{random_fact}*

---
*Updated on {current_date} via Ayman | Atlas DePIN 🇩🇿 | [Twitter](https://x.com/cotex5024) .* ### 🤝 How to Contribute
We welcome contributions from the community! Whether it's reporting a bug, improving documentation, or adding new DePIN insights, your help makes **Atlas-DePIN** stronger.

* **Read our guidelines:** Check out [CONTRIBUTING.md](CONTRIBUTING_TEMPLATE.md) for how to get started.
* **Have an idea?** Open a new [Issue](https://github.com/aymen015/Atlas-DePIN/issues) and let's discuss it."""

    # 4. التحديث على GitHub
    auth = Auth.Token(GH_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo("aymen015/Atlas-DePIN")

    try:
        contents = repo.get_contents("README.md")
        repo.update_file(contents.path, "feat: Update Atlas DePIN vision and market data", final_readme, contents.sha)
        print("Success: README updated with vision and intelligence!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_ai_bot()
