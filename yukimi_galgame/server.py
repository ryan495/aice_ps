"""雪見 Galgame 網頁的小伺服器。

- 提供 web/ 資料夾裡的網頁和立繪
- /api/chat：幫網頁去問 DeepSeek（API key 只留在這台電腦）
只用 Python 內建模組，不用另外安裝套件。
"""
import json
import socket
import sys
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
CONFIG_PATH = ROOT / "config.json"

EMOTIONS = ["平常", "開心", "害羞", "難過", "生氣", "壞笑", "驚訝", "睏", "拋媚眼"]

EMOTION_RULE = (
    "\n\n【表情標籤】每則回覆的最前面，一定要加上一個表情標籤，格式是【開心】這樣，"
    "只能從這些裡面選一個：" + "、".join(EMOTIONS) + "。標籤後面直接接你要說的話。"
    "標籤代表你說這句話時的表情，要跟內容的情緒一致。"
)


def load_config():
    if not CONFIG_PATH.exists():
        sys.exit("找不到 config.json：請把 config.example.json 複製一份改名成 config.json，再填入你的 DeepSeek API key。")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg.setdefault("api_base", "https://api.deepseek.com/v1")
    cfg.setdefault("model", "deepseek-flash")
    cfg.setdefault("temperature", 1.1)
    cfg.setdefault("max_history", 30)
    cfg.setdefault("port", 8848)
    cfg.setdefault("password", "")
    cfg.setdefault("mock", False)
    return cfg


CFG = load_config()
PERSONA = (ROOT / "persona.txt").read_text(encoding="utf-8").strip()
PRESETS = json.loads((ROOT / "presets.json").read_text(encoding="utf-8"))


def build_messages(history):
    msgs = [{"role": "system", "content": PERSONA + EMOTION_RULE}]
    for user, assistant in PRESETS:
        msgs.append({"role": "user", "content": user})
        msgs.append({"role": "assistant", "content": assistant})
    for m in history[-CFG["max_history"]:]:
        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
            msgs.append({"role": m["role"], "content": m["content"][:4000]})
    return msgs


def ask_llm(history):
    if CFG["mock"]:  # 測試用：不連 DeepSeek
        last = history[-1]["content"] if history else ""
        return f"【開心】嗯哼，姐姐收到囉～你剛剛說「{last[:20]}」對吧？"
    body = json.dumps({
        "model": CFG["model"],
        "messages": build_messages(history),
        "temperature": CFG["temperature"],
    }).encode("utf-8")
    req = urllib.request.Request(
        CFG["api_base"].rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + CFG["api_key"]},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, fmt, *args):  # 只印 API 呼叫，靜態檔不洗版
        if self.path.startswith("/api/"):
            super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_json(self, code, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        if self.path != "/api/chat":
            return self.send_json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 2_000_000:
                return self.send_json(413, {"error": "訊息太長了"})
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return self.send_json(400, {"error": "格式錯誤"})
        if CFG["password"] and req.get("password") != CFG["password"]:
            return self.send_json(401, {"error": "密碼錯誤"})
        try:
            reply = ask_llm(req.get("history", []))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:300]
            return self.send_json(502, {"error": f"DeepSeek 回傳錯誤 {e.code}：{detail}"})
        except Exception as e:
            return self.send_json(502, {"error": f"連不上 DeepSeek：{e}"})
        self.send_json(200, {"reply": reply})


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "你的電腦IP"


if __name__ == "__main__":
    if not (WEB / "sprites" / "manifest.json").exists():
        print("⚠ 找不到立繪：請把 yukimi_sprites 壓縮檔裡的東西放進 web/sprites/（裡面要有 manifest.json）")
    if not CFG["password"]:
        print("⚠ 沒有設定密碼：同一個 WiFi 的人都能用你的 DeepSeek 額度，建議在 config.json 填 password")
    port = CFG["port"]
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"雪見已經起床了～")
    print(f"  電腦打開： http://localhost:{port}")
    print(f"  手機打開： http://{lan_ip()}:{port}  （手機要連同一個 WiFi）")
    print("  關掉這個視窗就會停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
