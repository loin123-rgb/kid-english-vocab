// Cloudflare Pages Function — DeepL 翻譯 proxy
// URL: /translate (Pages 自動把 functions/translate.js 對到 /translate)
//
// 部署:Cloudflare Pages → 專案 → Settings → Environment variables
//   DEEPL_API_KEY = xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx
// 本機測試:`npx wrangler pages dev .`(吃同目錄 .dev.vars 或 .env)
//
// 跟 netlify/functions/translate.js 行為一致 — 環境變數名也一樣,
// 兩個平台都能跑同一份前端 code。

const FREE_ENDPOINT = "https://api-free.deepl.com/v2/translate";
const PRO_ENDPOINT = "https://api.deepl.com/v2/translate";

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

const json = (status, body) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });

export async function onRequest(context) {
  const { request, env } = context;

  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: cors });
  }

  const url = new URL(request.url);
  const q = url.searchParams.get("q");
  const source = url.searchParams.get("source");
  const target = url.searchParams.get("target");

  if (!q) return json(400, { error: "missing q" });

  // 從 env 拿 key,清掉常見的貼歪情況(空白、引號、誤連 KEY=)
  let key = (env.DEEPL_API_KEY || "").trim();
  if (
    (key.startsWith('"') && key.endsWith('"')) ||
    (key.startsWith("'") && key.endsWith("'"))
  ) {
    key = key.slice(1, -1).trim();
  }
  if (key.toUpperCase().startsWith("DEEPL_API_KEY=")) {
    key = key.slice("DEEPL_API_KEY=".length).trim();
  }
  if (!key) return json(500, { error: "DEEPL_API_KEY not configured" });

  // debug:?debug=1 不送 DeepL,只回報 function 端讀到的 key 形狀(永遠不洩漏 key 本身)
  if (url.searchParams.get("debug") === "1") {
    return json(200, {
      key_length: key.length,
      key_prefix: key.slice(0, 4),
      key_suffix: key.slice(-4),
      ends_with_fx: key.endsWith(":fx"),
      endpoint: key.endsWith(":fx") ? "free" : "pro",
      platform: "cloudflare",
    });
  }

  const endpoint = key.endsWith(":fx") ? FREE_ENDPOINT : PRO_ENDPOINT;
  const targetLang = toDeepLTarget(target);
  if (!targetLang) return json(400, { error: "invalid target lang: " + target });

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
      return json(res.status, {
        error: "deepl returned " + res.status,
        detail: detail.slice(0, 500),
      });
    }

    const data = await res.json();
    const t = (data.translations && data.translations[0]) || {};
    return json(200, {
      translated: t.text || "",
      detected_source_lang: t.detected_source_language || null,
      provider: "deepl",
    });
  } catch (err) {
    return json(502, { error: "fetch failed: " + err.message });
  }
}
