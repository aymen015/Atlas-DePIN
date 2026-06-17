import os
import random
from groq import Groq
from github import Github, Auth

def run_ai_bot():
    # 1. جلب الإعدادات
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GH_TOKEN = os.environ.get("GH_TOKEN")

    # 2. تحضير محتوى مبتكر ومتغير
    topics = [
        "latency reduction in decentralized GPU networks",
        "optimizing incentive mechanisms for node providers",
        "privacy-preserving computation in edge nodes",
        "cross-chain interoperability for DePIN resources"
    ]
    selected_topic = random.choice(topics)

    # 3. إعداد الـ Prompt الاحترافي
    prompt = f"""
    Act as a lead DePIN engineer. Provide a highly technical improvement proposal 
    for an AI compute project focusing on: {selected_topic}.
    - Use professional, concise language.
    - Provide exactly 3 bullet points.
    - Include specific technical terminology.
    - Keep it under 600 words.
    """

    # 4. استدعاء نموذج Groq
    client = Groq(api_key=GROQ_API_KEY)
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        temperature=0.8,  # رفع الحرارة قليلاً لزيادة الإبداع
    )
    
    innovation = chat_completion.choices[0].message.content
    print(f"AI Suggestion: {innovation}")

    # 5. تحديث GitHub
    auth = Auth.Token(GH_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo("aymen015/Atlas-DePIN")

    # إنشاء محتوى منظم
    content = f"# Atlas DePIN\n\n## 🚀 Latest AI-Driven Innovation\n*Focus Topic: {selected_topic.capitalize()}*\n\n{innovation}\n\n---\n*Updated automatically via AI Agent.*"
    
    try:
        contents = repo.get_contents("README.md")
        repo.update_file(contents.path, "feat: Professional AI intelligence update", content, contents.sha)
        print("Success: Updated repository with high-quality AI insight!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_ai_bot()
