const BASE = "/api";

async function get(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v != null && v !== "") url.searchParams.set(k, v);
  });
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function post(path) {
  const res = await fetch(`${BASE}${path}`, { method: "POST" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export function searchFirms({ q, state, min_aum, max_aum, strategy, has_drp, limit, offset } = {}) {
  return get(`${BASE}/search`, { q, state, min_aum, max_aum, strategy, has_drp, limit, offset });
}

export function getFirm(crd) {
  return get(`${BASE}/firms/${crd}`);
}

export function getFirmHoldings(crd) {
  return get(`${BASE}/firms/${crd}/holdings`);
}

export function getFirmPeers(crd) {
  return get(`${BASE}/firms/${crd}/peers`);
}

export function refreshFirm(crd) {
  return post(`/firms/${crd}/refresh`);
}

export function getHealth() {
  return get(`${BASE}/health`);
}

export async function streamInsight(crd, onChunk, onDone, onError) {
  const controller = new AbortController();
  try {
    const res = await fetch(`${BASE}/insight/${crd}`, {
      method: "POST",
      signal: controller.signal,
    });
    if (!res.ok) {
      onError?.(new Error(`${res.status} ${res.statusText}`));
      return () => {};
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    (async () => {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith("data: ")) continue;
            const payload = trimmed.slice(6);
            if (payload === "[DONE]") {
              onDone?.();
              return;
            }
            try {
              const parsed = JSON.parse(payload);
              if (parsed.error) {
                onError?.(new Error(parsed.error));
                return;
              }
              if (parsed.text) onChunk(parsed.text);
            } catch {
              // skip unparseable lines
            }
          }
        }
        onDone?.();
      } catch (err) {
        if (err.name !== "AbortError") onError?.(err);
      }
    })();
  } catch (err) {
    if (err.name !== "AbortError") onError?.(err);
  }
  return () => controller.abort();
}
