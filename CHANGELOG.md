# 📋 修改紀錄 / CHANGELOG

本檔案記錄專案的功能變更與修正歷程。最新的改動放最上面。

---

## v0.7 · 2026-04-30 · 繁體中文翻譯修正 ⚠️

### 修正(重要)
- **翻譯結果原本回簡體字** — `langCode()` 函式把 `zh-TW` 砍成 `zh`,MyMemory 預設給簡體
  - `langpair=en|zh` → 「你好」(簡體)
  - `langpair=en|zh-TW` → 「哈囉」(繁體) ✓
  - `langpair=en|zh-CN` → 「你好」(簡體)
- 改成保留完整 BCP-47 代碼直接送給 API

### 待觀察
- MyMemory 是社群翻譯記憶庫,**少數冷門字翻譯品質差**(例如 dragon → 「李耀軒」?!)— 若品質持續不佳,後續可能需換 DeepL / Google Translate API

---

## v0.6 · 2026-04-30 · LINE/FB 內建瀏覽器修正

### 修正
- **語音輸入(🎤)權限被拒** 顯示更友善的訊息:
  - 偵測到 LINE / FB / IG / 微信 / TikTok in-app 瀏覽器時,提示使用者「點右上角 ⋯ 改用外部瀏覽器」
  - 一般瀏覽器則提示「點網址列鎖頭重設權限」
  - 其他錯誤碼(`no-speech`, `audio-capture`, `network`)也都改寫成中文友善說明
- **LINE 內仍無法朗讀的問題**(LINE 假裝有 `speechSynthesis` 但實際不發聲):
  - 偵測到 in-app 瀏覽器 UA → 直接走 Google TTS 雲端 fallback,不再嘗試原生
  - Google fallback 失敗時跳出明確錯誤訊息(網路問題或 Google 端點變更)

### 已知限制
- 🎤 **語音輸入在 LINE 內無解** — LINE/FB/IG webview 直接擋麥克風,只能改用 Chrome/Safari 開
- 🔊 朗讀依賴 Google Translate TTS 端點(非官方公開 API,單次 ~200 字)

---

## v0.5 · 2026-04-30 · 雲端 TTS Fallback

### 新增
- **Google Translate TTS 雲端 fallback** — 給沒有 Web Speech API 的瀏覽器(LINE / FB / 微信 in-app webview)使用
- 統一的 `speakText(text, lang, rate, opts)` helper,涵蓋所有朗讀按鈕:
  - 翻譯分頁:🔊 朗讀
  - 發音練習:🔊 標準朗讀、🐢 慢速示範、跟讀循環
  - 單字寶盒大卡:🔊 唸給我聽、🐢 慢慢唸、🔊 唸例句

### 技術
- 偵測流程:有原生 → 試播 → 1.2 秒沒開始 → 自動切換雲端
- 雲端模式不支援「真正的慢速」,改用 `<audio>` 的 `playbackRate` 模擬

---

## v0.4 · 2026-04-30 · 例句

### 新增
- **單字大卡多一塊例句區**(藍色框):
  - 英文例句
  - 中文翻譯
  - 🔊 唸例句 按鈕
- 30 個記憶卡片全部補上 kid-friendly 的例句(動物 / 食物 / 動作 / 情緒)

### 範例
| Word | 例句 |
|---|---|
| dinosaur | There was a big dinosaur in the park. / 公園裡有一隻大恐龍。 |
| eye | Close your eyes and count to ten. / 閉上眼睛數到十。 |
| ice | I want some ice in my drink. / 我的飲料要加冰塊。 |

---

## v0.3 · 2026-04-30 · 單字寶盒分頁 + 國小+國中字庫 + 記憶卡片

### 新增
- **「翻譯」/「單字寶盒」分頁切換** — 翻譯與單字學習分開,小朋友體驗更聚焦
- **單字寶盒分頁** UI:
  - 全文搜尋(英文 / 中文)
  - 年級篩選(全部 / G6 / G7 / G8 / G9)
  - 「只看有圖」/「只看有記憶卡」勾選
  - 卡片網格(自動排列 120px+ 卡片)
- **單字大卡 modal**(點卡片彈出):
  - 大 emoji + word + 中譯 + 詞性 + 年級
  - 💡 記憶法區塊(黃框)
  - 🔊 唸給我聽 / 🐢 慢慢唸

### 資料
- 匯入 **2149 字台灣 K-9 英文字彙**
  - 國小 G6:833 字
  - 國中 G7:362 字
  - 國中 G8:449 字
  - 國中 G9:505 字
- 來源:[AppPeterPan/TaiwanSchoolEnglishVocabulary](https://github.com/AppPeterPan/TaiwanSchoolEnglishVocabulary)
- 自動把先前手寫的 EMOJI_MAP 對照進 vocab.json,**137 字**有 emoji 圖示
- 新增 **30 個記憶卡片**(`data/mnemonics.json`),分四類:
  - 🎵 **諧音記憶**(11 條):dinosaur → 呆腦獸 / panda → 胖達 / shark → 殺客
  - 👀 **字形聯想**(9 條):bed → b 和 d 是床柱 / eye → 兩個 e 是眼睛
  - ✨ **特徵綽號**(6 條):elephant → 水管鼻怪 / butterfly → 飛花紙片
  - 🧩 **拆字組合**(4 條):rainbow → rain + bow / understand → under + stand

---

## v0.2 · 2026-04-30 · 圖像對照

### 新增
- **譯文下方 emoji 對照條** — 翻譯時偵測譯文 + 原文中的常見字,顯示對應 emoji + 標籤
  - ~200 條中英對照詞庫(動物、食物、家庭、身體、交通、自然、學校、動作、情緒、招呼、顏色)
- 出場有彈跳動畫,小朋友看圖學字

### 修正
- 中文「一」原本被錯誤對照到 1️⃣ 數字 emoji(因為「一條蛇」的「一」是「a/an」不是「1」),已移除整段「數字 / 大小」對照避免誤導

---

## v0.1 · (本次工作開始前) · 翻譯小程式基礎版

開發本記錄前已存在的功能:
- 中 ⇄ 英即時翻譯(MyMemory 免費 API)
- 🎤 語音輸入(Web Speech Recognition)
- 🔊 譯文朗讀(Web Speech Synthesis)
- 🎯 發音練習:標準/慢速朗讀、語音辨識比對、按字逐字上色、給分(0-100)
- 🔁 跟讀循環(慢速 → 標準 → 自由 三輪)
- 📖 音標標示(英文 IPA 從 dictionaryapi.dev / 中文拼音從 pinyin-pro)
- 📚 練習紀錄(localStorage,最多 50 筆)

---

## 部署紀錄

- **2026-04-30:** 從 `Playground 2/.claude/worktrees/distracted-nobel-92128c/` 抽離成獨立專案 `kid-english-vocab/`,初始化 git repo,主分支 `main`
- **下一步:** 推到 GitHub → Netlify 連 repo → 自動部署

---

## 未來規劃 (Roadmap)

- [ ] 累積更多諧音卡片(目標 100-200 條,目前 30)
- [ ] 補上音標欄位(動態抓 dictionaryapi.dev,或一次性批量寫入 vocab.json)
- [ ] 新增「配對小遊戲」、「聽音選圖」遊戲化練習
- [ ] PWA(可加到手機桌面、可離線使用)
- [ ] 補上 **教育部國小英語基本字彙** 官方 300 字交叉驗證
- [ ] 兒童化視覺優化(更亮的配色、角色頭像、動畫反應)
