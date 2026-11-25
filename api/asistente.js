// Vercel Serverless Function para AgroDron IA (BD-N5: credenciales solo por variables de entorno)
export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(204).end();

  const vxKey = process.env.VERTEX_API_KEY || "";
  const orKey = process.env.OPENROUTER_API_KEY || "";

  if (req.method === "GET") {
    return res.status(200).json({
      estado: "ok",
      configurado: Boolean(vxKey || orKey),
      proveedores: { vertex: Boolean(vxKey), openrouter: Boolean(orKey) },
    });
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "Metodo no permitido" });
  }

  const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : (req.body || {});
  const mensaje = String(body.mensaje || "").trim();
  const historial = Array.isArray(body.historial) ? body.historial.slice(-10) : [];
  const systemPrompt = String(
    body.system_prompt ||
      "Eres AgroDron IA (Universidad de Caldas). Responde en espanol sobre el lote piloto Vereda La Cabana (1,0 ha, 25 m, 2.500 esperadas, 2.352 ground truth)."
  );

  if (!mensaje) {
    return res.status(400).json({ error: "El mensaje no puede estar vacio" });
  }

  const errores = [];

  if (vxKey) {
    const modelosV = [process.env.LLM_MODEL_VERTEX || "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"];
    for (const modeloV of modelosV) {
      try {
        const contents = historial
          .map((t) => ({ role: t.role === "assistant" ? "model" : "user", parts: [{ text: String(t.content || "") }] }))
          .concat([{ role: "user", parts: [{ text: mensaje }] }]);
        const url = `https://aiplatform.googleapis.com/v1/publishers/google/models/${modeloV}:generateContent?key=${encodeURIComponent(vxKey)}`;
        const r = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            systemInstruction: { parts: [{ text: systemPrompt }] },
            contents,
            generationConfig: { temperature: 0.3, maxOutputTokens: 650 },
          }),
        });
        if (r.ok) {
          const data = await r.json();
          const txt = (data?.candidates?.[0]?.content?.parts || []).map((p) => p.text || "").join("").trim();
          if (txt) return res.status(200).json({ respuesta: txt, proveedor: "vertex", modelo: modeloV });
        } else {
          errores.push(`vertex(${modeloV}): HTTP ${r.status}`);
        }
      } catch (e) {
        errores.push(`vertex(${modeloV}): ${e.message}`);
      }
    }
  }

  if (orKey) {
    const modelos = [process.env.LLM_MODEL_OPENROUTER || "google/gemini-2.5-flash", "openrouter/free", "openrouter/auto"];
    for (const modelo of modelos) {
      try {
        const msgs = [{ role: "system", content: systemPrompt }]
          .concat(historial.map((t) => ({ role: t.role === "assistant" ? "assistant" : "user", content: String(t.content || "") })))
          .concat([{ role: "user", content: mensaje }]);
        const r = await fetch("https://openrouter.ai/api/v1/chat/completions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${orKey}`,
            "HTTP-Referer": "https://agrodron.io",
            "X-Title": "AgroDron",
          },
          body: JSON.stringify({ model: modelo, messages: msgs, temperature: 0.3, max_tokens: 650 }),
        });
        if (r.ok) {
          const data = await r.json();
          const txt = data?.choices?.[0]?.message?.content?.trim();
          if (txt) return res.status(200).json({ respuesta: txt, proveedor: "openrouter", modelo });
        } else {
          errores.push(`openrouter(${modelo}): HTTP ${r.status}`);
        }
      } catch (e) {
        errores.push(`openrouter(${modelo}): ${e.message}`);
      }
    }
  }

  return res.status(200).json({
    respuesta: "",
    proveedor: "local-offline",
    motivo_fallback: errores.join("; "),
  });
}
