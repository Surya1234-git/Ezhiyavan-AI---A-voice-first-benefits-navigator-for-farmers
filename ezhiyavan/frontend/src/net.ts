export async function call(path: string, token?: string, opts: RequestInit = {}) {
  const r = await fetch("/api" + path, { ...opts, headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}) } });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export const post = (b: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(b) });
