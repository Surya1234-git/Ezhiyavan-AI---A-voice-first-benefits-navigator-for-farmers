import { useState } from "react";
import { call, post } from "./net";
import { Icon } from "./Icon";

export default function Partner() {
  const [tok, setTok] = useState(""); const [u, setU] = useState(""); const [p, setP] = useState(""); const [err, setErr] = useState("");
  const [cases, setCases] = useState<any[]>([]); const [sel, setSel] = useState<string | null>(null); const [d, setD] = useState<any>(null); const [note, setNote] = useState("");
  const [vals, setVals] = useState<Record<string, string>>({}); const [present, setPresent] = useState(false);
  const api = (path: string, opts?: RequestInit) => call(path, tok, opts);
  const guard = async (f: () => Promise<void>) => { setErr(""); try { await f(); } catch (e: any) { setErr(String(e.message).slice(0, 200)); } };
  const loadCases = (t: string) => call("/partner/cases", t).then(setCases);
  const open = (id: string) => guard(async () => { setSel(id); setD(await api(`/partner/cases/${id}`)); });

  if (!tok) return (<div className="wrap"><h1>Help centre login</h1>
    <input aria-label="User" placeholder="User" value={u} onChange={e => setU(e.target.value)} className="w100 mb8" />
    <input type="password" aria-label="Password" placeholder="Password" value={p} onChange={e => setP(e.target.value)} className="w100 mb8" />
    <button className="w100" onClick={() => guard(async () => { const r = await call("/partner/login", undefined, post({ user: u, password: p })); setTok(r.token); await loadCases(r.token); })}>Log in</button>
    {err && <p className="err">{err}</p>}</div>);

  return (<div className="wrap wrap900" ><h1>Help centre – {u}</h1>
    <p><small>You can only see farmers who gave this centre access. Every view and change is logged and visible to the farmer. Enter answers only with the farmer present and agreeing.</small></p>
    {err && <p className="err">{err}</p>}
    {!sel && <>{cases.length === 0 && <div className="card">No farmers have shared their case yet.</div>}
      {cases.map(c => <div className="card" key={c.farmer_ref}><b>{c.farmer_ref.slice(0, 8)}</b> · {c.language} · {c.answers} answers · {c.applications} applications
        <br /><small>shared {c.granted_at.slice(0, 10)}</small> <button className="fr p8" onClick={() => open(c.farmer_ref)}>Open</button></div>)}</>}
    {sel && d && <div>
      <button className="alt" onClick={() => { setSel(null); setD(null); loadCases(tok); }}>← All cases</button>
      <h3>Schemes (household)</h3>{d.results.map((r: any) => <div className="card" key={r.scheme_id}><b>{r.name}</b> <span className={`badge ${r.status}`}>{r.status}</span>
        <ul>{r.trace.map((x: any) => <li key={x.rule_id}><small><Icon n={x.result === "pass" ? "check" : x.result === "fail" ? "cross" : "help"} /> {x.text}</small></li>)}</ul></div>)}
      {d.members.length > 0 && <><h3>Family members (consented)</h3>{d.members.map((m: any) => <div className="card" key={m.member_id}><b>{m.relationship}, {m.age}</b>
        {m.results.map((r: any) => <div key={r.scheme_id}>{r.name} <span className={`badge ${r.status}`}>{r.status}</span></div>)}</div>)}</>}
      <p><small>Consent given {d.consent.granted_at.slice(0, 10)} · the farmer can withdraw it at any time.</small></p>
      {d.family_issues?.map((x: any, i: number) => <p key={i} className="warn-text"><Icon n="warn" /> Family record: {x.kind}</p>)}{d.doc_issues?.map((x: any, i: number) => <p key={i} className="err"><Icon n="warn" /> Documents: {x.kind}</p>)}
      <label className="card block notice" ><input type="checkbox" checked={present} onChange={e => setPresent(e.target.checked)} /> <b>The farmer is present and agrees to me entering or reviewing this information.</b></label>
      <h3>Unanswered questions</h3>{d.unanswered.length === 0 && <small>None.</small>}
      {d.unanswered.map((q: any) => <div className="card" key={q.field}>{q.question}<div className="row mt8" >
        {q.kind === "bool" ? <><button disabled={!present} onClick={() => guard(async () => { await api(`/partner/cases/${sel}/profile`, post({ field: q.field, value: true, farmer_present: present })); await open(sel); })}>Yes</button>
          <button className="alt" disabled={!present} onClick={() => guard(async () => { await api(`/partner/cases/${sel}/profile`, post({ field: q.field, value: false, farmer_present: present })); await open(sel); })}>No</button></>
          : <><input value={vals[q.field] || ""} onChange={e => setVals(v => ({ ...v, [q.field]: e.target.value }))} />
            <button onClick={() => guard(async () => { const raw = vals[q.field] || ""; await api(`/partner/cases/${sel}/profile`, post({ field: q.field, value: q.kind === "number" ? Number(raw) : raw, farmer_present: present })); await open(sel); })}>Save</button></>}</div></div>)}
      <h3>Documents</h3>{d.documents.map((x: any) => <div className="card" key={x.id}><b>{x.doc_type}</b> {Object.keys(x.confirmed).length ? <><Icon n="check" /> confirmed by farmer</> : <><Icon n="clock" /> not confirmed</>}
        <br /><small>{JSON.stringify(x.confirmed)} {x.quality_warnings.length > 0 && <><Icon n="warn" /> {x.quality_warnings.join(", ")}</>}</small><br /><small>Read from document – authenticity not verified. {x.checked_by_a_person && <><Icon n="user" /> reviewed by a person: {x.review_outcome}</>}</small>
        <div className="row mt6" >{["looks_consistent", "needs_attention"].map(o => <button key={o} className="alt p8" disabled={!present} 
          onClick={() => guard(async () => { await api(`/partner/cases/${sel}/documents/${x.id}/review`, post({ outcome: o, farmer_present: present })); await open(sel); })}>{o === "looks_consistent" ? "Looks consistent" : "Needs attention"}</button>)}</div></div>)}
      <h3>Applications (self-reported by the farmer)</h3>{d.applications.map((a: any, i: number) => <div className="card" key={i}>{a.scheme_id} – {a.status} {a.reference_number && `· ref ${a.reference_number}`}</div>)}
      <h3>Reminders</h3>{d.reminders.length === 0 && <small>None.</small>}{d.reminders.map((r: any, i: number) => <div key={i}><Icon n="clock" /> {r.kind}: {r.doc_type || r.scheme_id} {r.date || ""}</div>)}
      <h3>Add a note for the farmer</h3><div className="row"><input value={note} onChange={e => setNote(e.target.value)} maxLength={500} />
        <button disabled={!note} onClick={() => guard(async () => { await api(`/partner/cases/${sel}/notes`, post({ text: note })); setNote(""); })}>Add</button></div>
    </div>}</div>);
}
