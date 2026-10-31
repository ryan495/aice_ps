# 雪見 Galgame 網頁

在電腦上跑一個小程式，手機或電腦用瀏覽器打開，就能跟雪見聊天。

- 每句回覆會依情緒換表情（平常、開心、害羞、難過、生氣、壞笑、驚訝、睏、拋媚眼）
- 文字跑出來時嘴巴會動，平常會眨眼、輕輕呼吸
- 右上角 👗 可以換 8 套衣服，📜 看對話紀錄，⚙️ 輸入密碼、清除紀錄
- 背景顏色會隨時間變化（早上、白天、傍晚、晚上）

## 第一次設定

1. **安裝 Python**：到 https://www.python.org/downloads/ 下載安裝，安裝畫面記得勾選「Add python.exe to PATH」。
2. **放立繪**：把立繪包解壓縮，讓資料夾變成這樣：
   ```
   yukimi_galgame/web/sprites/manifest.json
   yukimi_galgame/web/sprites/home_apron/neutral.webp
   ……
   ```
3. **填設定**：把 `config.example.json` 複製一份，改名成 `config.json`，用記事本打開：
   - `api_key`：貼上你的 DeepSeek API key
   - `password`：自己取一個密碼，手機第一次打開時要輸入
   - `model`：預設 `deepseek-flash`，跟你 AstrBot 裡用的一樣

## 每次使用

1. 雙擊 `start.bat`，會跳出一個黑色視窗，上面寫著兩個網址。
2. **電腦**：瀏覽器打開 `http://localhost:8848`
3. **手機**：連同一個 WiFi，瀏覽器打開視窗上寫的 `http://192.168.x.x:8848`
   - 第一次會要你輸入密碼，按右上角 ⚙️ 輸入 `config.json` 裡的 password。
   - 可以用瀏覽器的「加到主畫面」，用起來就像 App。
4. 不用的時候，把黑色視窗關掉就好。

> Windows 第一次可能會跳出「防火牆」詢問，要選「允許」（私人網路），手機才連得進來。

## 改人設

- `persona.txt`：雪見的人設，跟 AstrBot 裡的是同一份。改完重新啟動 `start.bat` 才會生效。
- `presets.json`：預設對話（示範她怎麼講話）。每句回覆前面的【開心】之類是表情標籤，要保留。

## 注意

- 這個網頁跟 AstrBot 是分開的：Telegram 那邊的記憶這裡看不到，這裡的對話紀錄也只存在你用的那個瀏覽器裡。
- 在外面（不同 WiFi）要用的話，可以兩邊都裝 Tailscale，再用 Tailscale 給的網址連回家。
- API key 只存在電腦的 `config.json`，不會傳到手機。不要把 `config.json` 傳給別人。
- 測試用：把 `config.json` 的 `mock` 改成 `true`，就不會真的連 DeepSeek，她只會固定回一句話。
