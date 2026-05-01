// Cloudflare Pages Function — Azure Speech (Neural TTS) proxy
// URL: /tts?text=hello&voice=en-US-AriaNeural&phoneme=h%C9%99l%C5%8D
//
// 環境變數(Cloudflare Pages → Settings → Environment variables):
//   AZURE_TTS_KEY    — Speech Service 的 KEY 1 或 KEY 2
//   AZURE_TTS_REGION — 部署的 region,像 eastus / eastasia / japaneast
//
// 回傳:audio/mpeg 二進位(MP3),前端用 Audio element 直接播。
// 失敗回 JSON 錯誤訊息。
//
// SSML phoneme 標籤可以給 IPA(/æ/、/θ/ 之類)讓 Azure 精準唸出單一音 —
// 這是 phonics 卡片點「音」的關鍵。

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

const xmlEscape = (s) =>
  String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");

// 組 SSML — 如果有 phoneme 就用 <phoneme> 包字母音,否則直接唸 text
const buildSSML = (text, voice, phoneme, lang) => {
  const safeText = xmlEscape(text || "x");
  const inner = phoneme
    ? `<phoneme alphabet="ipa" ph="${xmlEscape(phoneme)}">${safeText}</phoneme>`
    : safeText;
  return (
    `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="${lang}">` +
    `<voice name="${voice}">${inner}</voice>` +
    `</speak>`
  );
};

export async function onRequest(context) {
  const { request, env } = context;

  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: cors });
  }

  const url = new URL(request.url);
  const text = url.searchParams.get("text") || "";
  const phoneme = url.searchParams.get("phoneme") || "";
  const voice = url.searchParams.get("voice") || "en-US-AriaNeural";
  const lang = url.searchParams.get("lang") || "en-US";
  const rate = url.searchParams.get("rate") || "";

  if (!text && !phoneme) {
    return json(400, { error: "missing text or phoneme" });
  }

  let key = (env.AZURE_TTS_KEY || "").trim();
  if (
    (key.startsWith('"') && key.endsWith('"')) ||
    (key.startsWith("'") && key.endsWith("'"))
  ) key = key.slice(1, -1).trim();
  const region = (env.AZURE_TTS_REGION || "").trim().toLowerCase();
  if (!key || !region) {
    return json(500, {
      error: "AZURE_TTS_KEY 或 AZURE_TTS_REGION 沒設定",
    });
  }

  let ssml = buildSSML(text, voice, phoneme, lang);
  // 想調速度的話包一層 <prosody rate="...">
  if (rate) {
    ssml = ssml.replace(
      /<voice([^>]*)>/,
      `<voice$1><prosody rate="${xmlEscape(rate)}">`,
    ).replace(/<\/voice>/, "</prosody></voice>");
  }

  const endpoint = `https://${region}.tts.speech.microsoft.com/cognitiveservices/v1`;

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent": "kid-english-vocab/0.1",
      },
      body: ssml,
    });

    if (!res.ok) {
      const detail = await res.text();
      return json(res.status, {
        error: "azure tts " + res.status,
        detail: detail.slice(0, 500),
      });
    }

    const audio = await res.arrayBuffer();
    return new Response(audio, {
      status: 200,
      headers: {
        ...cors,
        "Content-Type": "audio/mpeg",
        // 短暫 CDN 快取(同一段話/IPA 短時間內常被點)
        "Cache-Control": "public, max-age=86400",
      },
    });
  } catch (err) {
    return json(502, { error: "fetch failed: " + err.message });
  }
}
