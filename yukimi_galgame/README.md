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
3. **填設定**：第一次雙擊 `start.bat` 時，程式會自動建立 `config.json` 並用記事本打開，填好存檔後再執行一次 `start.bat`。（也可以自己把 `config.example.json` 複製一份改名成 `config.json`；Windows 預設會隱藏副檔名，小心不要變成 `config.json.json`。）先選模式：

   | `backend` | 說明 |
   |---|---|
   | `"astrbot"`（預設，推薦） | 透過 AstrBot 說話：人設、LivingMemory 記憶、插件都跟 Telegram 共用。AstrBot 要開著。 |
   | `"deepseek"` | 網頁自己問 DeepSeek，不需要 AstrBot，但看不到 AstrBot 的記憶。 |

   其他欄位：
   - `astrbot_api_key`：AstrBot 的 API Key（建立方式見下面）
   - `api_key`：你的 DeepSeek API key。AstrBot 模式也建議填，用來判斷每句話的表情；不填的話會改用關鍵字判斷，比較不準。
   - `password`：自己取一個密碼，手機第一次打開時要輸入
   - `model`：預設 `deepseek-flash`，跟你 AstrBot 裡用的一樣

## AstrBot 模式要做的兩件事

1. **建立 API Key**：打開 AstrBot 管理網頁（`http://localhost:6185`），在設定裡找「API Key」或「開發者」頁面，新增一把 Key，權限勾 **chat**，把產生的 Key 貼到 `config.json` 的 `astrbot_api_key`。Key 只會顯示一次，記得先複製。
2. **讓記憶跨視窗共用**：LivingMemory 預設是「每個聊天視窗各記各的」，網頁和 Telegram 會被當成兩個視窗。
   - AstrBot 管理網頁 →「插件」→ LivingMemory →「視圖」→ dashboard →「設定」，在「訪問與隔離」那一類裡把「記憶作用域模式」（memory_scope_mode）改成 **global**，存檔後重載插件。
   - 想把之前 Telegram 存的舊記憶也搬過去共用，在 Telegram 傳 `/lmem migrate-scope global`（先預覽），確認沒問題再傳 `/lmem migrate-scope global apply`。它會先自動備份。

> 網頁跟 Telegram 是兩個不同的「對話視窗」：剛剛幾句的上下文不會互通，但長期記憶（LivingMemory）在設成 global 後會共用。

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

- `deepseek` 模式下，這個網頁跟 AstrBot 是分開的：Telegram 那邊的記憶這裡看不到。
- 📜 對話紀錄只存在你用的那個瀏覽器裡（AstrBot 模式下 AstrBot 也會另外存一份）。
- AstrBot 模式下，改人設請改 AstrBot 裡的人格設定；`persona.txt` 和 `presets.json` 只在 `deepseek` 模式用到。
- 在外面（不同 WiFi）要用的話，可以兩邊都裝 Tailscale，再用 Tailscale 給的網址連回家。
- API key 只存在電腦的 `config.json`，不會傳到手機。不要把 `config.json` 傳給別人。
- 測試用：把 `config.json` 的 `mock` 改成 `true`，就不會真的連 DeepSeek，她只會固定回一句話。
