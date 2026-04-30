// DeepL 翻譯 proxy — 把 API key 藏在 Netlify 環境變數,前端打不到 key
//
// 部署:Netlify dashboard → Site configuration → Environment variables
//   DEEPL_API_KEY = xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx
//
// 本機測試:`netlify dev`(會讀同目錄 .env);若沒裝就讓前端走 MyMemory fallback。

const FREE_ENDPOINT = "https://api-free.deepl.com/v2/translate";
const PRO_ENDPOINT = "https://api.deepl.com/v2/translate";

// 前端送 BCP-47 (zh-TW / en-US),DeepL 用自己一套 (ZH-HANT / EN-US)
const toDeepLTarget = (code) => {
  if (!code) return null;
  const c = code.toLowerCase();
  if (c === "zh-tw" || c === "zh-hant") return "ZH-HANT";
  if (c === "zh-cn" || c === "zh-hans" || c === "zh") return "ZH-HANS";
  if (c.startsWith("en-gb")) return "EN-GB";
  if (c.startsWith("en")) return "EN-US";
  return code.toUpperCase();
};

const toDeepLSource = (code) => {
  if (!code) return null;
  const c = code.toLowerCase();
  if (c.startsWith("zh")) return "ZH";
  if (c.startsWith("en")) return "EN";
  return code.split("-")[0].toUpperCase();
};

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

exports.handler = async (event) => {
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 204, headers: cors, body: "" };
  }

  const { q, source, target } = event.queryStringParameters || {};
  if (!q) {
    return {
      statusCode: 400,
      headers: { ...cors, "Content-Type": "application/json" },
      body: JSON.stringify({ error: "missing q" }),
    };
  }

  const key = process.env.DEEPL_API_KEY;
  if (!key) {
    return {
      statusCode: 500,
      headers: { ...cors, "Content-Type": "application/json" },
      body: JSON.stringify({ error: "DEEPL_API_KEY not configured" }),
    };
  }

  const endpoint = key.endsWith(":fx") ? FREE_ENDPOINT : PRO_ENDPOINT;
  const targetLang = toDeepLTarget(target);
  if (!targetLang) {
    return {
      statusCode: 400,
      headers: { ...cors, "Content-Type": "application/json" },
      body: JSON.stringify({ error: "invalid target lang: " + target }),
    };
  }

  const params = new URLSearchParams();
  params.append("text", q);
  params.append("target_lang", targetLang);
  const sourceLang = toDeepLSource(source);
  if (sourceLang) params.append("source_lang", sourceLang);

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        Authorization: "DeepL-Auth-Key " + key,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });

    if (!res.ok) {
      const detail = await res.text();
      return {
        statusCode: res.status,
        headers: { ...cors, "Content-Type": "application/json" },
        body: JSON.stringify({
          error: "deepl returned " + res.status,
          detail: detail.slice(0, 500),
        }),
      };
    }

    const data = await res.json();
    const t = (data.translations && data.translations[0]) || {};
    return {
      statusCode: 200,
      headers: { ...cors, "Content-Type": "application/json" },
      body: JSON.stringify({
        translated: t.text || "",
        detected_source_lang: t.detected_source_language || null,
        provider: "deepl",
      }),
    };
  } catch (err) {
    return {
      statusCode: 502,
      headers: { ...cors, "Content-Type": "application/json" },
      body: JSON.stringify({ error: "fetch failed: " + err.message }),
    };
  }
};
