"""雪見 Galgame 網頁的小伺服器。

- 提供 web/ 資料夾裡的網頁和立繪
- /api/chat：幫網頁去問 DeepSeek（API key 只留在這台電腦）
只用 Python 內建模組，不用另外安裝套件。
"""
import json
import re
import socket
import sys
import urllib.error
import urllib.request
import uuid
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
        # 第一次啟動：自動從範本建立 config.json，並用記事本打開讓你填
        CONFIG_PATH.write_text((ROOT / "config.example.json").read_text(encoding="utf-8"), encoding="utf-8")
        print("已經幫你建立 config.json，請在打開的記事本裡填好 Key 和密碼，存檔後再重新執行 start.bat。")
        try:
            import os
            os.startfile(str(CONFIG_PATH))  # 只有 Windows 有
        except Exception:
            print(f"設定檔在：{CONFIG_PATH}")
        sys.exit(0)
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg.setdefault("api_base", "https://api.deepseek.com/v1")
    cfg.setdefault("model", "deepseek-flash")
    cfg.setdefault("temperature", 1.1)
    cfg.setdefault("max_history", 30)
    cfg.setdefault("port", 8848)
    cfg.setdefault("password", "")
    cfg.setdefault("mock", False)
    # backend：deepseek＝網頁自己問 DeepSeek；astrbot＝透過 AstrBot（共用人設、記憶、插件）
    cfg.setdefault("backend", "deepseek")
    cfg.setdefault("astrbot_url", "http://127.0.0.1:6185")
    cfg.setdefault("astrbot_api_key", "")
    cfg.setdefault("astrbot_username", "achuu")
    return cfg


CFG = load_config()
PERSONA = (ROOT / "persona.txt").read_text(encoding="utf-8").strip()
PRESETS = json.loads((ROOT / "presets.json").read_text(encoding="utf-8"))
SESSION_FILE = ROOT / "astrbot_session.txt"
TAG_RE = re.compile(r"[【\[](" + "|".join(EMOTIONS) + r")[】\]]")


def has_deepseek_key():
    key = str(CFG.get("api_key", ""))
    return bool(key) and not key.startswith("在這裡")


# ---------- AstrBot 模式 ----------
def astrbot_session_id():
    """網頁固定用同一個 AstrBot 對話視窗，第一次自動建立。"""
    if SESSION_FILE.exists():
        return SESSION_FILE.read_text(encoding="utf-8").strip()
    sid = "yukimi-galgame-" + uuid.uuid4().hex[:12]
    SESSION_FILE.write_text(sid, encoding="utf-8")
    return sid


def ask_astrbot(message):
    body = json.dumps({
        "message": message,
        "session_id": astrbot_session_id(),
        "username": CFG["astrbot_username"],
        "enable_streaming": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        CFG["astrbot_url"].rstrip("/") + "/api/v1/chat",
        data=body,
        headers={"Content-Type": "application/json", "X-API-Key": CFG["astrbot_api_key"]},
    )
    parts = []
    with urllib.request.urlopen(req, timeout=180) as resp:
        if "json" in resp.headers.get("Content-Type", ""):   # AstrBot 回錯誤時是 JSON
            data = json.loads(resp.read().decode("utf-8"))
            raise RuntimeError(data.get("message") or data.get("data") or str(data))
        for raw in resp:                                      # 其餘是 SSE：data: {...}
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            try:
                ev = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            kind = ev.get("type")
            if kind == "plain" and ev.get("chain_type") not in ("tool_call", "tool_call_result", "reasoning"):
                if isinstance(ev.get("data"), str) and ev["data"].strip():
                    parts.append(ev["data"])
            elif kind == "error":
                raise RuntimeError(f"AstrBot 回覆失敗：{ev.get('data')}")
            elif kind == "end":
                break
    text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("AstrBot 沒有回覆內容")
    return text


KEYWORDS = [
    ("生氣", ["哼！", "哼，", "生氣", "討厭", "不理你", "壞孩子", "欺負"]),
    ("害羞", ["害羞", "臉紅", "不好意思", "討厭啦", "///", "才沒有"]),
    ("難過", ["難過", "心疼", "嗚", "捨不得"]),
    ("驚訝", ["欸？", "什麼？", "真的假的", "蛤", "！？", "?!"]),
    ("睏", ["睏", "想睡", "呵欠", "晚安", "好累"]),
    ("壞笑", ["嘿嘿", "哦——", "被我抓到", "你該不會", "壞壞"]),
    ("拋媚眼", ["♡", "❤", "親一下", "喜歡你"]),
    ("開心", ["XD", "笑死", "哈哈", "好耶", "太好了", "～", "開心"]),
]


def guess_emotion(text):
    if has_deepseek_key() and not CFG["mock"]:
        try:
            body = json.dumps({
                "model": CFG["model"],
                "temperature": 0,
                "max_tokens": 8,
                "messages": [
                    {"role": "system", "content": "你是表情判斷器。看這句台詞，從清單選一個最符合說話者表情的詞，只回那個詞：" + "、".join(EMOTIONS)},
                    {"role": "user", "content": text[:500]},
                ],
            }).encode("utf-8")
            req = urllib.request.Request(
                CFG["api_base"].rstrip("/") + "/chat/completions", data=body,
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + CFG["api_key"]},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                ans = json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"]
            for e in EMOTIONS:
                if e in ans:
                    return e
        except Exception:
            pass  # 判斷失敗就用關鍵字
    for emo, words in KEYWORDS:
        if any(w in text for w in words):
            return emo
    return "平常"


def reply_via_astrbot(history):
    last = next((m["content"] for m in reversed(history) if m.get("role") == "user"), "")
    if CFG["mock"]:
        text = f"（AstrBot 模式測試）姐姐收到囉～你說「{last[:20]}」XD"
    else:
        text = ask_astrbot(last)
    m = TAG_RE.search(text)
    emo = m.group(1) if m else guess_emotion(text)
    return f"【{emo}】" + TAG_RE.sub("", text).strip()


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
        via = "AstrBot" if CFG["backend"] == "astrbot" else "DeepSeek"
        try:
            history = req.get("history", [])
            reply = reply_via_astrbot(history) if CFG["backend"] == "astrbot" else ask_llm(history)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:300]
            return self.send_json(502, {"error": f"{via} 回傳錯誤 {e.code}：{detail}"})
        except Exception as e:
            return self.send_json(502, {"error": f"{via} 出問題了：{e}"})
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
    if CFG["backend"] == "astrbot":
        print(f"模式：透過 AstrBot（{CFG['astrbot_url']}），人設和記憶跟 Telegram 共用")
        if not CFG["astrbot_api_key"] or CFG["astrbot_api_key"].startswith("在這裡"):
            print("⚠ 還沒填 astrbot_api_key：請在 AstrBot 管理網頁建立一把有 chat 權限的 API Key")
        if not has_deepseek_key():
            print("  （沒填 DeepSeek api_key：表情會用關鍵字判斷，準確度差一點）")
    else:
        print("模式：直接連 DeepSeek（不會用到 AstrBot 的記憶）")
    if CFG["password"] == "自己取一個密碼":
        print("⚠ 密碼還是範本裡的「自己取一個密碼」，建議改成你自己的")
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
