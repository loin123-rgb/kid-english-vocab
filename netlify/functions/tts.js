// Netlify Function — Azure Speech (Neural TTS) proxy
// URL (透過 netlify.toml redirect): /tts?text=hello&voice=...&phoneme=...
// 直接路徑:/.netlify/functions/tts
//
// 跟 functions/tts.js (Cloudflare 版) 行為一致 — 環境變數名也一樣。

const xmlEscape = (s) =>
  String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");

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

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

const json = (status, body) => ({
  statusCode: status,
  headers: { ...cors, "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

exports.handler = async (event) => {
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 204, headers: cors, body: "" };
  }

  const params = event.queryStringParameters || {};
  const text = params.text || "";
  const phoneme = params.phoneme || "";
  const voice = params.voice || "en-US-AriaNeural";
  const lang = params.lang || "en-US";
  const rate = params.rate || "";

  if (!text && !phoneme) {
    return json(400, { error: "missing text or phoneme" });
  }

  let key = (process.env.AZURE_TTS_KEY || "").trim();
  if (
    (key.startsWith('"') && key.endsWith('"')) ||
    (key.startsWith("'") && key.endsWith("'"))
  ) key = key.slice(1, -1).trim();
  const region = (process.env.AZURE_TTS_REGION || "").trim().toLowerCase();
  if (!key || !region) {
    return json(500, {
      error: "AZURE_TTS_KEY 或 AZURE_TTS_REGION 沒設定",
    });
  }

  let ssml = buildSSML(text, voice, phoneme, lang);
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
    return {
      statusCode: 200,
      headers: {
        ...cors,
        "Content-Type": "audio/mpeg",
        "Cache-Control": "public, max-age=86400",
      },
      body: Buffer.from(audio).toString("base64"),
      isBase64Encoded: true,
    };
  } catch (err) {
    return json(502, { error: "fetch failed: " + err.message });
  }
};
