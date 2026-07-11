"""
Vercel Serverless Function — 代理 DeepSeek API 调用
"""
from http.server import BaseHTTPRequestHandler
import json
import os
from openai import OpenAI


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL) if DEEPSEEK_API_KEY else None


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}

        messages = body.get("messages", [])
        temperature = body.get("temperature", 0.7)
        max_tokens = body.get("max_tokens", 2048)

        if not client:
            result = _fallback(messages)
        else:
            try:
                resp = client.chat.completions.create(
                    model=body.get("model", "deepseek-chat"),
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                result = resp.choices[0].message.content
            except Exception as e:
                result = f"[API Error: {e}]"

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"content": result}, ensure_ascii=False).encode("utf-8"))


def _fallback(messages):
    last = messages[-1]["content"] if messages else ""
    sys = messages[0]["content"] if messages else ""
    if "客服" in sys:
        return "您好！我是智选商城智能客服小智 👋 有什么可以帮您的？\n\n> 📋 知识库命中：退换政策v2.3\n> 🎯 意图识别：咨询（95%）"
    return "## 🗺️ 旅行规划\n\n**Day 1**：抵达 → 入住酒店 → 海边漫步\n\n| 项目 | 费用 |\n|------|------|\n| 交通 | ¥1,200 |\n| 住宿 | ¥1,800 |\n| 合计 | ¥5,000 |"
