# 🔧 開發筆記 / Dev Notes

技術決策、踩過的坑、診斷過程紀錄。CHANGELOG 寫「改了什麼」,本檔寫「為什麼這樣改」與未來可能要動的方向。

---

## 1. 翻譯 API 與繁體中文

### 已知問題:`zh` 被 MyMemory 視為簡體
原本 `langCode()` 函式把 `zh-TW` 砍成 `zh` 才送 API,結果都回簡體。直接 curl 驗證:

```bash
curl "https://api.mymemory.translated.net/get?q=hello&langpair=en|zh"
# → "你好"  (簡體)

curl "https://api.mymemory.translated.net/get?q=hello&langpair=en|zh-TW"
# → "哈囉"  (繁體) ✓

curl "https://api.mymemory.translated.net/get?q=hello&langpair=en|zh-CN"
# → "你好"  (簡體對照)
```

**修法(v0.7):** 直接送完整 BCP-47 (`zh-TW`),`langCode()` 改成 passthrough。

### MyMemory 的品質風險
MyMemory 是「社群貢獻 + 翻譯記憶庫」,**冷門字會回垃圾資料**。實測:

```
dragon (en → zh-TW) → "李耀軒"   ← 顯然是某使用者把人名翻譯丟進去的污染
```

短期可接受(主要常見字翻譯都 OK),但若後續品質不穩,候選替代 API:

| API | 免費額度 | 品質 | 需要 API key | 繁中支援 |
|---|---|---|---|---|
| MyMemory(現用) | 5000 字/天/IP | 中(社群污染) | 否 | `zh-TW` |
| **DeepL** | 50 萬字/月 | 最佳 | 是(免費註冊) | `ZH-HANT` |
| Google Cloud Translate | 50 萬字/月 | 高 | 是(信用卡綁定) | `zh-TW` |
| LibreTranslate(自架或公開) | 視 instance | 中 | 視 instance | 變數,部分用 `zt` |
| Microsoft Translator | 200 萬字/月 | 高 | 是 | `zh-Hant` |

**推薦遷移路徑:** 若需升級,DeepL 是 CP 值最高(品質最好,額度夠日常使用,只要免費註冊拿 key)。

---

## 2. 朗讀 (TTS) 策略

### 雙引擎:原生 + Google 雲端 fallback

```
使用者點 🔊
    ↓
偵測 in-app browser (LINE/FB/IG/微信/TikTok)?
    ↓ 是                        ↓ 否
直接走 Google TTS 雲端       試原生 speechSynthesis.speak()
    ↓                            ↓ 1.2 秒沒實際發聲
                              切到 Google TTS
```

### 為什麼 in-app 直接走雲端
測試發現 LINE webview 會宣稱有 `'speechSynthesis' in window === true`,但 `speak()` 實際不發聲。`onstart` 不一定觸發、`speaking` 屬性也不可靠 → 1.2 秒探針抓不到「沉默式失敗」。最穩定的解法是看 UA 直接決定。

### Google TTS 端點的注意事項
```
https://translate.google.com/translate_tts?ie=UTF-8&q=...&tl=...&client=tw-ob
```

- **非官方公開 API**,僅供 Google Translate 網頁內部使用,理論上他們哪天改規則就會掛
- 實務上社群已用 5+ 年穩定
- 單次請求約 200 字限制,我們的單字、例句都遠低於此
- 用 `<audio>` element 播放,**不能加 `crossOrigin = "anonymous"`**(會觸發 CORS preflight,Google 沒回對應 header,直接失敗)

### 萬一 Google TTS 端點掛了的備案
依優先序:
1. **ResponsiveVoice**(需付費或免費版含 watermark / 浮水印)
2. **VoiceRSS**(免費 350 次/天,有 API key)
3. **自架 server 走 Coqui-TTS / Piper**(完全自主,需 hosting)
4. **Google Cloud TTS**(每月免費 100 萬字,需綁信用卡)
5. 直接放棄朗讀,顯示「請改用原生瀏覽器(Chrome / Safari)」

---

## 3. 語音輸入 (STT) 在 in-app browser 永遠不會動

LINE / FB / IG / 微信 webview **直接擋麥克風**(不是權限問題,是 webview 政策不開放),這是平台限制,**沒辦法用前端程式繞過**。

只能透過 UX 引導使用者:
- 偵測 in-app UA → 顯示提示:「語音輸入需在 Chrome / Safari 開,請點右上角 ⋯ 在外部瀏覽器開啟」
- 一般瀏覽器但被使用者拒絕 → 提示「點網址列鎖頭重設權限」
- 其他錯誤(無聲、找不到麥克風、網路) → 各自的中文友善訊息

---

## 4. 資料來源與授權

### 字彙資料
- **來源:** [AppPeterPan/TaiwanSchoolEnglishVocabulary](https://github.com/AppPeterPan/TaiwanSchoolEnglishVocabulary)(GitHub)
- **授權:** ❌ **無 LICENSE 檔**
- **風險評估:** 字表本身(教育部公告字彙)屬公開資料、無著作權;但**中譯文是作者自編**,嚴格說屬該作者。本專案目前定位「給小朋友的非商業教學網頁」風險低,但若後續轉商用須:
  - 開 issue 詢問作者授權,或
  - 改用 [rocVocabularies](https://github.com/XiaoPanPanKevinPan/rocVocabularies)(只有英文字、依教育部 ODT 整理),自己補中譯

### 記憶卡片(諧音/字形/特徵/拆字)
全為自製內容,版權歸本專案。

---

## 5. 為什麼 G6 用大考中心 1 級而非教育部國小 300 字

**理由:** AppPeterPan 沒有獨立的「國小 300 字」檔案,但其「1 級.json」(大考中心七千字第 1 級,~1666 字)涵蓋國小 + 國中初階字。把 1 級扣掉 G7-9 既有字 = 833 字,作為 G6(國小高年級)。

**代價:** 不是嚴格意義上「教育部國小英語基本字彙 300 字」,而是更廣的基礎字集。

**未來改善:** 找到教育部官方 ODT/PDF → 標記哪些是「真·國小必背 300」,作為 `level: "elementary-core"` 子集。

---

## 6. 部署架構

```
GitHub repo (kid-english-vocab)
    ↓ git push
Netlify (auto-deploy on main branch)
    ↓
https://xxx.netlify.app/
    ↓
靜態 HTML + 兩個 JSON,fetch 自相同 origin
```

- **Build command:** 留空(純靜態)
- **Publish dir:** 留空 / `.`(根目錄)
- **環境變數:** 無(目前所有 API 不需要 key)

### 若未來要加需要 key 的 API
- 不能把 key 放前端(會洩漏)
- 解法 1:Netlify Functions(serverless proxy)
- 解法 2:Cloudflare Workers
- 解法 3:自己架小 server(Vercel / Render free tier)

---

## 7. 未做但已知的小問題

- 譯文裡的「dragon → 李耀軒」這種 MyMemory 污染資料,目前無前端過濾
- 例句目前只 30 個(隨記憶卡片走),vocab 中其他 2119 字沒例句 → 之後可考慮 dictionaryapi.dev 動態抓
- 音標目前只有「翻譯模式 → 發音練習」會抓,單字寶盒大卡沒顯示音標(可加)
- 跟讀循環模式下,雲端 TTS fallback 沒測過完整三輪流程
