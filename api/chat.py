"""
Vercel Python Handler — 静态页面 + DeepSeek API 流式代理
"""
from http.server import BaseHTTPRequestHandler
import json
import os
from openai import OpenAI

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1") if DEEPSEEK_API_KEY else None

_HTML = None


def _get_html():
    global _HTML
    if _HTML is None:
        try:
            with open("index.html", "r", encoding="utf-8") as f:
                _HTML = f.read()
        except:
            _HTML = "<h1>Loading...</h1>"
    return _HTML


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self._cors_headers()
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(_get_html().encode("utf-8"))

    def do_POST(self):
        if not self.path.startswith("/api"):
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
        messages = body.get("messages", [])
        temperature = body.get("temperature", 0.7)
        max_tokens = body.get("max_tokens", 2048)
        stream = body.get("stream", False)

        if not client:
            result = _fallback(messages)
            self._send_json({"content": result})
            return

        if stream:
            self._stream_response(messages, temperature, max_tokens)
        else:
            self._normal_response(messages, temperature, max_tokens)

    def _stream_response(self, messages, temperature, max_tokens):
        """流式返回：chunked transfer encoding"""
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self._cors_headers()
            self.end_headers()

            for chunk in resp:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    encoded = text.encode("utf-8")
                    self.wfile.write(encoded)
                    self.wfile.flush()
        except Exception as e:
            error_text = f"\n\n---\n> ⚠️ 流式输出中断: {e}"
            self.wfile.write(error_text.encode("utf-8"))
            self.wfile.flush()

    def _normal_response(self, messages, temperature, max_tokens):
        """非流式返回 JSON"""
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result = resp.choices[0].message.content
        except Exception as e:
            result = f"[API Error: {e}]"
        self._send_json({"content": result})

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def _fallback(messages):
    last = messages[-1]["content"] if messages else ""
    sys = messages[0]["content"] if messages else ""
    if "客服" in sys:
        return "您好！我是智选商城智能客服小智 👋 有什么可以帮您的？\n\n> 📋 知识库命中：退换政策v2.3\n> 🎯 意图识别：咨询（95%）"
    return "## 🗺️ 旅行规划\n\n**Day 1**：抵达 → 入住酒店 → 海边漫步\n\n| 项目 | 费用 |\n|------|------|\n| 交通 | ¥1,200 |\n| 住宿 | ¥1,800 |\n| 合计 | ¥5,000 |"
