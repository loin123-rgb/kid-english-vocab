# 🌐 即時翻譯 + 單字寶盒

給小朋友的中英翻譯 + 單字學習網頁。內含 2149 個台灣國小至國中英文字彙,搭配諧音/字形/特徵記憶卡片,讓背單字變成解謎遊戲。

## ✨ 功能

### 翻譯模式
- 中 ⇄ 英即時翻譯(MyMemory 免費 API)
- 🎤 語音輸入(Chrome / Edge / Android)
- 🔊 朗讀譯文(瀏覽器內建 TTS)
- 🎯 發音練習 + 自動評分 + 跟讀循環
- 📖 音標標示(IPA / 拼音)
- 圖像對照:譯文配 emoji,小朋友看圖學字
- 練習紀錄(localStorage)

### 單字寶盒模式
- 2149 字按年級瀏覽(國小 G6 833 字 + 國中 G7-9 1316 字)
- 篩選:年級 / 只看有圖 / 只看有記憶卡 / 全文搜尋
- 點卡片跳出大卡:emoji + 中譯 + 記憶法 + 例句 + 朗讀
- 🎯 **大卡內練發音** — 直接錄自己唸,即時上色 + 0-100 分,可切換練「單字」或「例句」
- 📝 **例句自動補齊** — 沒手寫的字自動從 [dictionaryapi.dev](https://dictionaryapi.dev) 抓真實例句,失敗則用模板兜底,結果存 localStorage 下次秒開
- 4 種記憶法標籤:🎵 諧音 / 👀 字形 / ✨ 特徵 / 🧩 拆字

## 🚀 本機執行

### 純前端(MyMemory 翻譯,不用 DeepL)
需要 http server(瀏覽器擋住 file:// 抓 JSON)。

```bash
# 隨便用一種:
npx serve .                  # Node
python -m http.server 3000   # Python
```

然後開 http://localhost:3000

### 本機要測 DeepL backup(走 Netlify Function)
1. `cp .env.example .env` 然後把你的 DeepL Free key 貼進 `DEEPL_API_KEY=`
2. `npm i -g netlify-cli`
3. `netlify dev`
4. 開瀏覽器自動跳出的 http://localhost:8888

`.env` 已加入 `.gitignore`,不會 commit。

## ☁️ 部署

純靜態網站,任何免費平台都能部署:

| 平台 | 步驟 |
|---|---|
| **Netlify** | 連 GitHub repo → Build command 留空 → Publish directory `.` → Deploy |
| **Vercel** | 連 GitHub repo → Framework preset: Other → Deploy |
| **GitHub Pages** | Settings → Pages → Source: main / `/` → Save |

## 📁 結構

```
.
├── index.html           # 唯一的應用入口
├── data/
│   ├── vocab.json       # 2149 字主資料
│   └── mnemonics.json   # 記憶卡片內容(30 條起跳,持續擴充)
├── README.md            # 你正在看的檔案
├── CHANGELOG.md         # 修改紀錄(改了什麼)
└── DEV_NOTES.md         # 開發日記(為什麼這樣改、踩過的坑、未來方向)
```

## 📚 資料來源

單字資料改編自 [AppPeterPan/TaiwanSchoolEnglishVocabulary](https://github.com/AppPeterPan/TaiwanSchoolEnglishVocabulary):
- 國中三年 (G7-9):來自 `國一/國二/國三.json`
- 國小 (G6):來自 `1級.json`(扣除已收錄於 G7-9 的字)

記憶卡片內容(諧音、字形聯想、特徵綽號、拆字)為自製。

## 🎯 記憶法分類

| 類型 | 範例 |
|---|---|
| 🎵 諧音記憶 | dinosaur → 呆腦獸 / panda → 胖達 |
| 👀 字形聯想 | bed → b/d 是床柱,e 是躺著的人 |
| ✨ 特徵綽號 | elephant → 水管鼻怪 |
| 🧩 拆字組合 | rainbow → rain (雨) + bow (弓) |

## 📱 行動裝置

UI 已響應式設計,手機可用。注意:
- ✅ 翻譯、單字寶盒、朗讀、例句:全平台 OK
- ⚠️ 語音輸入 (Web Speech Recognition):iOS Safari 不支援
- ✅ Android Chrome:全功能

## 🔧 後續可擴充

- [ ] 累積更多諧音卡片(目標 100-200)
- [ ] 補上音標(動態抓 dictionaryapi.dev)
- [ ] 配對小遊戲 / 聽音選圖
- [ ] PWA(可離線、加到桌面)
