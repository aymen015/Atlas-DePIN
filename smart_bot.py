import os
from groq import Groq
from github import Github, Auth

def run_ai_bot():
    # الأسرار (Secrets) يتم جلبها تلقائياً من إعدادات GitHub
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GH_TOKEN = os.environ.get("GH_TOKEN")

    # 1. إعداد Groq
    client = Groq(api_key=GROQ_API_KEY)
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": "Give me a one-sentence technical improvement for a DePIN AI compute project."}],
        model="llama-3.3-70b-versatile",
    )
    idea = chat_completion.choices[0].message.content
    print(f"AI Suggestion: {idea}")

    # 2. إعداد GitHub
    auth = Auth.Token(GH_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo("aymen015/Atlas-DePIN")

    # تحديث الملف
    content = f"# Atlas DePIN\n\n## Latest AI Innovation\n{idea}\n\n*Updated automatically via AI.*"
    
    try:
        contents = repo.get_contents("README.md")
        repo.update_file(contents.path, "feat: AI-driven update", content, contents.sha)
        print("Success: Updated via GitHub Action!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_ai_bot()
