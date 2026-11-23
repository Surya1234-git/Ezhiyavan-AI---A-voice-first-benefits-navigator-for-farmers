import { useState } from "react";
import { call, post } from "./net";
import { Icon } from "./Icon";

export default function Admin() {
  const [tok, setTok] = useState(""); const [me, setMe] = useState(""); const [p, setP] = useState(""); const [err, setErr] = useState("");
  const [ready, setReady] = useState<any>(null); const [form, setForm] = useState<any>(null); const [trust, setTrust] = useState<any>(null); const [diff, setDiff] = useState<any>(null); const [list, setList] = useState<any[]>([]); const [json, setJson] = useState(""); const [audit, setAudit] = useState<any[]>([]); const [msg, setMsg] = useState(""); const [impact, setImpact] = useState<any>(null); const [reports, setReports] = useState<any[]>([]);
  const api = (path: string, opts?: RequestInit) => call(path, tok, opts);
  const guard = async (f: () => Promise<void>) => { setErr(""); setMsg(""); try { await f(); } catch (e: any) { setErr(String(e.message).slice(0, 600)); } };
  const refresh = async (t = tok) => { setList(await call("/admin/schemes", t)); setAudit(await call("/admin/audit", t)); setTrust(await call("/admin/trust", t)); setReady(await call("/admin/readiness", t)); setImpact(await call("/admin/impact", t).catch(() => null)); setReports(await call("/admin/reports", t).catch(() => [])); };

  if (!tok) return (<div className="wrap"><h1>Scheme reviewer login</h1>
    <input aria-label="User" placeholder="User" value={me} onChange={e => setMe(e.target.value)} className="w100 mb8" />
    <input type="password" aria-label="Password" placeholder="Password" value={p} onChange={e => setP(e.target.value)} className="w100 mb8" />
    <button className="w100" onClick={() => guard(async () => { const r = await call("/admin/login", undefined, post({ user: me, password: p })); setTok(r.token); await refresh(r.token); })}>Log in</button>
    {err && <p className="err">{err}</p>}</div>);

  return (<div className="wrap wrap900" ><h1>Scheme management – {me}</h1>
    {trust && <div className={"card " + (trust.trustworthy ? "ok-bg" : "bad-bg")}><b>{trust.trustworthy ? <Icon n="check" /> : <Icon n="warn" />} Can farmers trust what they see?</b><br />{trust.summary}
      <br /><small>{trust.shown_to_farmers} scheme(s) shown to farmers · {trust.schemes.filter((x: any) => x.expired || x.expiring_within_30_days).length} expired or expiring · {trust.schemes.filter((x: any) => x.stale_review).length} overdue for review</small></div>}
    {impact && <div className="card"><h3 className="mt0">Impact (anonymised totals)</h3>
      {impact.small_sample && <p><small><Icon n="warn" /> Fewer than 5 farmers: do not read statistics into these numbers.</small></p>}
      <div className="row">{([["Farmers", impact.farmers_total], ["Screened", impact.farmers_screened], ["With a possible scheme", impact.farmers_with_potential_scheme], ["Active in 30 days", impact.active_last_30_days]] as [string, number][]).map(([k, v]) => <div key={k}><b className="big28">{v}</b><br /><small>{k}</small></div>)}</div>
      {Object.keys(impact.potential_matches_by_scheme).length > 0 && <p><b>Possible matches by scheme</b><br />{Object.entries(impact.potential_matches_by_scheme).map(([k, v]) => <small key={k}>{k}: {String(v)} · </small>)}</p>}
      {impact.most_common_missing_documents.length > 0 && <p><b>Most common missing documents</b><br />{impact.most_common_missing_documents.map((x: [string, number]) => <small key={x[0]}>{x[0]}: {x[1]} · </small>)}</p>}
      <small>{impact.note}</small></div>}
    {reports.length > 0 && <div className="card"><h3 className="mt0">Rule reports ({reports.filter(r => r.status === "open").length} open)</h3>
      {reports.slice(0, 20).map(r => <div key={r.id} className="rowline py6"><small>{r.at.slice(0, 10)} · {r.scheme_id} {r.rule_id} · {r.status}</small><br />{r.text}
        {r.status === "open" && <div><button className="alt p6"  onClick={() => guard(async () => { await api(`/admin/reports/${r.id}/close`, { method: "POST" }); await refresh(); })}>Mark reviewed</button></div>}</div>)}</div>}
    <p><small>A rule goes live only after a DIFFERENT reviewer approves it against the official source. All actions are audited.</small></p>
    {err && <pre className="err prewrap">{err}</pre>}{msg && <p>{msg}</p>}
    {list.map(s => <div className="card" key={s.scheme_id}><b>{s.name}</b> <span className={"badge " + (s.status === "verified" ? "green" : "amber")}>{s.status}</span>
      <br /><small>{s.scheme_id} · v{s.version} · {s.rule_count} rules · {s.evidence_blockers} evidence gap(s) · approvals {(s.approvals || []).length} · submitted by {s.submitted_by ?? "—"} · verified {s.last_verified ?? "never"} {s.approved_by && `by ${s.approved_by}`}</small>
      {s.review_notes && <p><small><Icon n="edit" /> {s.review_notes}</small></p>}<br /><a href={s.source} target="_blank" rel="noreferrer">official source</a>
      <div className="row mt8" >
        <button className="alt" onClick={() => guard(async () => setDiff({ id: s.scheme_id, ...(await api(`/admin/schemes/${s.scheme_id}/diff`)) }))}>Compare / blockers</button>
        <button className="alt" onClick={() => guard(async () => setJson(JSON.stringify(await api(`/admin/schemes/${s.scheme_id}`), null, 2)))}>Load JSON</button>
        <button disabled={s.status === "verified"} onClick={() => guard(async () => { const r = await api(`/admin/schemes/${s.scheme_id}/approve`, { method: "POST" }); setMsg(r.status === "verified" ? "Verified." : `Approval recorded (${r.approvals} of ${r.required}). Another reviewer is needed.`); await refresh(); })}>Approve</button></div></div>)}
    {diff && <div className="card"><b>{diff.id}: {diff.high_impact ? "high-impact change (two reviewers)" : "low-impact change (one reviewer)"}</b>
      {diff.blockers.length > 0 ? <ul>{diff.blockers.map((b: string) => <li key={b}><small><Icon n="ban" /> {b}</small></li>)}</ul> : <p><Icon n="check" /> No evidence blockers.</p>}
      <pre className="prewrap fs12">{diff.diff ? JSON.stringify(diff.diff, null, 1) : "No earlier verified version to compare with (new scheme)."}</pre><button className="alt" onClick={() => setDiff(null)}>Close</button></div>}
    {ready && <div className="card"><h3 className="mt0">Production readiness: {ready.passed} of {ready.total} checks passed {ready.release_ready ? <><Icon n="check" /> release ready</> : <><Icon n="ban" /> not release ready</>}</h3>
      <small>Status comes from evidence. Scheme checks are computed from the live data; Tamil OCR and benchmark checks are computed from attached machine-generated reports; the rest need evidence and an independent reviewer.</small>
      {ready.checks.map((c: any) => <div key={c.id} className="rowline py8">
        <span className={"badge " + (c.status === "passed" ? "green" : c.status === "failed" ? "red" : c.status === "in_progress" ? "amber" : "grey")}>{c.status.replace("_", " ")}</span> <b>{c.title}</b>
        <br /><small>{c.kind} · tested {c.tested_on ?? "never"} · reviewer {c.reviewer ?? "—"}{c.history ? ` · ${c.history} record(s)` : ""}</small>
        {c.evidence && <div><small>Evidence: {c.evidence}</small></div>}{c.outstanding?.map((o: string) => <div key={o}><small><Icon n="ban" /> {o}</small></div>)}
        {c.kind !== "auto" && <button className="alt p6 mt4"  onClick={() => setForm({ id: c.id, kind: c.kind, status: "in_progress", reviewer: "", tested_on: new Date().toISOString().slice(0, 10), evidence: "", report: "" })}>Record result</button>}</div>)}
      {form && <div className="card grey-bg"><b>Record: {form.id}</b>
        {form.kind === "evidence" && <select aria-label="Status" value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>{["not_started", "in_progress", "passed", "failed"].map(x => <option key={x}>{x}</option>)}</select>}
        <input aria-label="Reviewer" placeholder="Independent reviewer (not you)" value={form.reviewer} onChange={e => setForm({ ...form, reviewer: e.target.value })} className="w100 my6" />
        <input aria-label="Tested on" placeholder="Tested on (YYYY-MM-DD)" value={form.tested_on} onChange={e => setForm({ ...form, tested_on: e.target.value })} className="w100 mb6" />
        <textarea aria-label="Evidence" rows={3} placeholder="Evidence: https link to the report, or what was run and the result" value={form.evidence} onChange={e => setForm({ ...form, evidence: e.target.value })} className="w100" />
        {form.kind === "report" && <textarea aria-label="Report JSON" rows={5} placeholder="Paste the JSON produced by doc_eval.py --json or run_eval.py --json" value={form.report} onChange={e => setForm({ ...form, report: e.target.value })} className="w100 mono" />}
        <div className="row"><button onClick={() => guard(async () => { const body: any = { status: form.kind === "evidence" ? form.status : null, reviewer: form.reviewer, tested_on: form.tested_on, evidence: form.evidence }; if (form.kind === "report") body.report = JSON.parse(form.report || "null");
            const r = await api(`/admin/readiness/${form.id}`, post(body)); setMsg(`Recorded: ${r.status}`); setForm(null); await refresh(); })}>Save</button><button className="alt" onClick={() => setForm(null)}>Cancel</button></div></div>}</div>}
    <h3>Submit / edit a scheme (JSON)</h3>
    <textarea rows={14} className="w100 mono" value={json} onChange={e => setJson(e.target.value)} />
    <button onClick={() => guard(async () => { await api("/admin/schemes", { method: "POST", body: json }); setMsg("Saved as pending_review. Another reviewer must approve."); await refresh(); })}>Submit for review</button>
    <h3>Audit log</h3>{audit.slice(0, 30).map((a, i) => <div key={i}><small>{a.at.slice(0, 19)} · {a.actor} · {a.action} {a.scheme_id ?? ""} {a.farmer_id ? "· farmer " + a.farmer_id.slice(0, 8) : ""}</small></div>)}</div>);
}
