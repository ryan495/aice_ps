// 雪見 Galgame 網頁
(() => {
  const $ = (id) => document.getElementById(id);
  const sprite = $("sprite"), textEl = $("text"), input = $("input"), sendBtn = $("send");

  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* 無痕模式等情況存不了就算了 */ } },
  };

  let manifest = null;
  let outfit = store.get("yukimi_outfit", null);
  let history = store.get("yukimi_history", []);
  let emotion = "平常";
  let talking = false;
  let busy = false;
  let typing = null;           // 打字機計時器
  let idleTimer = null;        // 一陣子沒說話就回到平常表情
  const cache = {};

  // ---------- 立繪 ----------
  const src = (file, o = outfit) => `sprites/${o}/${file}`;

  function preload(o) {
    for (const ex of Object.values(manifest.expressions)) {
      for (const f of Object.values(ex)) {
        const url = src(f, o);
        if (!cache[url]) { const img = new Image(); img.src = url; cache[url] = img; }
      }
    }
  }

  function frame(kind) {          // kind: idle / talk / blink
    if (!manifest) return;
    const ex = manifest.expressions[emotion] || manifest.expressions["平常"];
    const file = ex[kind] || ex.idle;
    const url = src(file);
    if (sprite.getAttribute("src") !== url) sprite.setAttribute("src", url);
  }

  function setEmotion(e) {
    emotion = manifest.expressions[e] ? e : "平常";
    frame(talking ? "talk" : "idle");
    clearTimeout(idleTimer);
    if (emotion !== "平常") idleTimer = setTimeout(() => { if (!talking) { emotion = "平常"; frame("idle"); } }, 40000);
  }

  // 眨眼：只有有眨眼圖的表情會眨
  (function blinkLoop() {
    setTimeout(() => {
      const ex = manifest && (manifest.expressions[emotion] || {});
      if (manifest && !talking && ex.blink) {
        frame("blink");
        setTimeout(() => { if (!talking) frame("idle"); }, 130);
      }
      blinkLoop();
    }, 2500 + Math.random() * 3500);
  })();

  // ---------- 文字 ----------
  const KNOWN = () => (manifest ? Object.keys(manifest.expressions) : ["平常"]).join("|");
  function parseReply(raw) {
    const m = raw.match(new RegExp(`^\\s*[【\\[](${KNOWN()})[】\\]]\\s*`));
    const emo = m ? m[1] : "平常";
    const text = raw.replace(new RegExp(`[【\\[](${KNOWN()})[】\\]]`, "g"), "").trim();
    return { emo, text };
  }

  function showSystem(msg) {
    stopTyping();
    textEl.className = "system";
    textEl.textContent = msg;
  }

  function stopTyping() {
    if (typing) { clearInterval(typing.timer); typing = null; }
    talking = false;
    frame("idle");
  }

  function typeOut(text) {
    stopTyping();
    textEl.className = "";
    textEl.textContent = "";
    let i = 0, mouthOpen = false, pause = 0, beat = 0;
    talking = true;
    typing = {
      text,
      timer: setInterval(() => {
        if (pause > 0) { pause--; if (mouthOpen) { mouthOpen = false; frame("idle"); } return; }
        if (i >= text.length) { stopTyping(); textEl.textContent = text; return; }
        const ch = text[i++];
        textEl.textContent = text.slice(0, i);
        textEl.scrollTop = textEl.scrollHeight;
        if ("，。！？…、,.!?～~\n".includes(ch)) { pause = 4; return; }
        if (++beat % 2 === 0) {        // 每兩個字開合一次，比較自然
          mouthOpen = !mouthOpen;
          frame(mouthOpen ? "talk" : "idle");
        }
      }, 55),
    };
  }

  // 點對話框可以直接顯示全文
  textEl.addEventListener("click", () => { if (typing) { const t = typing.text; stopTyping(); textEl.textContent = t; } });

  // ---------- 聊天 ----------
  function saveHistory() { store.set("yukimi_history", history.slice(-200)); }

  async function send(msg) {
    if (busy || !msg.trim()) return;
    busy = true; sendBtn.disabled = true;
    history.push({ role: "user", content: msg.trim() });
    saveHistory();
    stopTyping();
    setEmotion("平常");
    textEl.className = "";
    textEl.innerHTML = '<span class="cursor">…</span>';
    try {
      const res = await fetch("api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ history: history.slice(-40), password: store.get("yukimi_pw", "") }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 401) {
        history.pop(); saveHistory();
        showSystem("密碼不對喔。按右上角 ⚙️ 輸入 config.json 裡的密碼。");
        openPanel("panel-settings");
        return;
      }
      if (!res.ok) throw new Error(data.error || `伺服器錯誤 ${res.status}`);
      history.push({ role: "assistant", content: data.reply });
      saveHistory();
      const { emo, text } = parseReply(data.reply);
      setEmotion(emo);
      typeOut(text);
    } catch (e) {
      history.pop(); saveHistory();
      showSystem(`（連線出問題了：${e.message}）\n剛剛那句沒送出去，可以再傳一次。`);
    } finally {
      busy = false; sendBtn.disabled = false;
    }
  }

  $("input-row").addEventListener("submit", (e) => {
    e.preventDefault();
    const msg = input.value;
    input.value = ""; autosize();
    send(msg);
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("input-row").requestSubmit(); }
  });
  function autosize() { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 120) + "px"; }
  input.addEventListener("input", autosize);

  // ---------- 面板 ----------
  function openPanel(id) {
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("hidden", p.id !== id || !p.classList.contains("hidden")));
    if (id === "panel-log") renderLog();
    if (id === "panel-outfit") renderOutfits();
  }
  $("btn-outfit").onclick = () => openPanel("panel-outfit");
  $("btn-log").onclick = () => openPanel("panel-log");
  $("btn-settings").onclick = () => { $("password").value = store.get("yukimi_pw", ""); openPanel("panel-settings"); };
  document.querySelectorAll(".panel .close").forEach((b) => (b.onclick = () => b.closest(".panel").classList.add("hidden")));

  function renderOutfits() {
    const list = $("outfit-list");
    list.innerHTML = "";
    for (const [key, name] of Object.entries(manifest.outfits)) {
      const b = document.createElement("button");
      b.className = "outfit" + (key === outfit ? " active" : "");
      b.innerHTML = `<div class="thumb" style="background-image:url('${src("neutral.webp", key)}')"></div>`;
      b.append(name);
      b.onclick = () => {
        outfit = key; store.set("yukimi_outfit", key); preload(key);
        const wrap = $("sprite-wrap");
        wrap.style.opacity = 0;
        setTimeout(() => { frame("idle"); wrap.style.opacity = 1; }, 250);
        renderOutfits();
      };
      list.append(b);
    }
  }

  function renderLog() {
    const list = $("log-list");
    list.innerHTML = "";
    if (!history.length) { list.textContent = "還沒有聊天紀錄。"; return; }
    for (const m of history) {
      const row = document.createElement("div");
      row.className = "row " + m.role;
      const who = document.createElement("span");
      who.className = "who";
      who.textContent = m.role === "user" ? "阿徹" : "雪見";
      row.append(who, m.role === "assistant" ? parseReply(m.content).text : m.content);
      list.append(row);
    }
    list.scrollTop = list.scrollHeight;
  }

  $("btn-save-pw").onclick = () => { store.set("yukimi_pw", $("password").value); $("panel-settings").classList.add("hidden"); };
  $("btn-clear").onclick = () => {
    if (!confirm("確定要清除所有對話紀錄嗎？雪見會忘記這段對話。")) return;
    history = []; saveHistory();
    $("panel-settings").classList.add("hidden");
    setEmotion("開心"); typeOut("嗯？剛剛聊到哪了……算了，阿徹，我們重新開始吧～");
  };

  // ---------- 背景隨時間變化 ----------
  function updateBg() {
    const h = new Date().getHours();
    $("bg").className = h >= 5 && h < 9 ? "morning" : h >= 9 && h < 17 ? "day" : h >= 17 && h < 19 ? "evening" : "night";
  }
  updateBg(); setInterval(updateBg, 60000);

  // ---------- 開始 ----------
  fetch("sprites/manifest.json").then((r) => {
    if (!r.ok) throw new Error();
    return r.json();
  }).then((m) => {
    manifest = m;
    if (!outfit || !manifest.outfits[outfit]) outfit = manifest.default_outfit || Object.keys(manifest.outfits)[0];
    preload(outfit);
    const last = [...history].reverse().find((x) => x.role === "assistant");
    if (last) {
      const { emo, text } = parseReply(last.content);
      setEmotion(emo); frame("idle");
      textEl.textContent = text;
    } else {
      setEmotion("開心");
      typeOut("阿徹，你來啦～今天想跟姐姐聊什麼？");
    }
  }).catch(() => showSystem("找不到立繪檔案：請把 yukimi_sprites 壓縮檔裡的東西放進 web/sprites/ 資料夾（裡面要有 manifest.json）。"));
})();
