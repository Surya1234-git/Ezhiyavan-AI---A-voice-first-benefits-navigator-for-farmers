import { useEffect, useRef, useState } from "react";
import { Lang, T, speechLang } from "./i18n";
import { Icon } from "./Icon";
import { Logo, Illustration } from "./Logo";

const api = async (path: string, opts?: RequestInit) => {
  const isForm = opts?.body instanceof FormData;
  const r = await fetch("/api" + path, { credentials: "include", ...opts,
    headers: { ...(isForm ? {} : { "Content-Type": "application/json" }), "X-Requested-With": "ezhiyavan" } });
  if (r.status === 401 && !path.startsWith("/auth") && path !== "/me/session") location.reload();
  if (!r.ok) throw new Error(await r.text());
  return r.json();
};
const J = (b: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(b) });

function speak(text: string, lang: Lang, slow = false) {
  if (!("speechSynthesis" in window)) return;
  const u = new SpeechSynthesisUtterance(text); u.lang = speechLang[lang]; u.rate = slow ? 0.7 : 0.95;
  speechSynthesis.cancel(); speechSynthesis.speak(u);
}
function listen(lang: Lang, cb: (t: string) => void, hooks?: { onInterim?: (t: string) => void; onEnd?: () => void }): any {   // the recogniser (so it can be stopped), or null when this browser has no speech recognition
  const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  if (!SR) return null;
  const r = new SR(); r.lang = speechLang[lang]; r.interimResults = !!hooks?.onInterim;
  r.onresult = (e: any) => { const res = e.results[e.results.length - 1]; const txt = res[0].transcript; if (res.isFinal === false && hooks?.onInterim) hooks.onInterim(txt); else cb(txt); };
  r.onerror = () => hooks?.onEnd?.(); r.onend = () => hooks?.onEnd?.(); r.start(); return r;
}

export default function App() {
  const [lang, setLang] = useState<Lang>("ta");
  const [fid, setFid] = useState<string | null | undefined>(undefined);   // session lives in an HttpOnly cookie
  useEffect(() => { api("/me/session").then(() => setFid("me")).catch(() => setFid(null)); }, []);
  const [tab, setTab] = useState<"chat" | "results" | "family" | "docs" | "wallet" | "apps">("chat"); const [more, setMore] = useState(false);
  const t = (k: string) => T[k][lang];

  if (fid === undefined) return null;
  if (!fid) return <Welcome lang={lang} setLang={setLang} onLogin={() => setFid("me")} />;
  return (
    <div className="wrap app">
      <h1 className="brand"><Logo size={36} /> Ezhiyavan AI</h1>
      <select aria-label="Language / மொழி / भाषा" value={lang} onChange={e => setLang(e.target.value as Lang)}>
        <option value="ta">தமிழ்</option><option value="en">English</option><option value="hi">हिन्दी</option></select>
      <nav className="tabbar" aria-label="Main"><div className="tabs">
        {([["chat", "mic", "navAsk"], ["results", "search", "results"], ["docs", "doc", "navDocs"], ["apps", "clipboard", "navApps"]] as const).map(([k, ic, lb]) =>
          <button key={k} className={tab === k ? "tab on" : "tab"} aria-current={tab === k ? "page" : undefined} onClick={() => { setTab(k); setMore(false); }} aria-label={t(lb)}><Icon n={ic} /><small className="inherit">{t(lb)}</small></button>)}
        <button className={"tab" + (tab === "family" || tab === "wallet" ? " on" : "")} aria-expanded={more} aria-controls="more-panel" aria-label={t("tabMore")} onClick={() => setMore(!more)}><Icon n="more" /><small className="inherit">{t("tabMore")}</small></button></div>
        {more && <div className="more" id="more-panel" role="group" aria-label={t("tabMore")}>{([["family", "family", "navFamily"], ["wallet", "wallet", "navBenefits"]] as const).map(([k, ic, lb]) =>
          <button key={k} className={tab === k ? "" : "alt"} onClick={() => { setTab(k); setMore(false); }}><Icon n={ic} /> {t(lb)}</button>)}</div>}
      </nav>
      {tab === "chat" && <Chat fid={fid} lang={lang} onDone={() => setTab("results")} />}
      {tab === "results" && <Results fid={fid} lang={lang} />}
      {tab === "family" && <Family lang={lang} />}
      {tab === "docs" && <Docs lang={lang} />}
      {tab === "wallet" && <Wallet lang={lang} />}
      {tab === "apps" && <Apps fid={fid} lang={lang} />}
      <p><button className="alt" onClick={async () => { await api("/auth/logout", { method: "POST" }).catch(() => 0); setFid(null); }}>{t("logout")}</button></p>
      <DeleteAll lang={lang} onDone={() => setFid(null)} />
    </div>);
}

function LangPick({ lang, setLang }: { lang: Lang; setLang: (l: Lang) => void }) {
  return (<div className="row lang" role="group" aria-label="Language / மொழி / भाषा">{([["ta", "தமிழ்"], ["en", "English"], ["hi", "हिन्दी"]] as const).map(([k, n]) =>
    <button key={k} className={lang === k ? "" : "alt"} aria-pressed={lang === k} onClick={() => setLang(k)}>{n}</button>)}</div>);
}

function Welcome({ lang, setLang, onLogin }: { lang: Lang; setLang: (l: Lang) => void; onLogin: () => void }) {
  const [phone, setPhone] = useState(""); const [code, setCode] = useState(""); const [sent, setSent] = useState(false);
  const [agree, setAgree] = useState(false); const [err, setErr] = useState("");
  const run = async (f: () => Promise<void>) => { setErr(""); try { await f(); } catch (e: any) { setErr(String(e.message).slice(0, 120)); } };
  return (<div className="wrap"><h1 className="brand"><Logo /> Ezhiyavan AI</h1><Illustration /><p>{T.tagline[lang]}</p>
    <LangPick lang={lang} setLang={setLang} />
    <ol className="steps3"><li><Icon n="mic" /><span>{T.stepSpeak[lang]}</span></li><li><Icon n="check" /><span>{T.stepConfirm[lang]}</span></li><li><Icon n="doc" /><span>{T.stepRules[lang]}</span></li></ol>
    <div className="card"><small>{T.consent[lang]}</small>
      <p><label><input type="checkbox" checked={agree} onChange={e => setAgree(e.target.checked)} /> {T.agree[lang]}</label></p></div>
    <input inputMode="numeric" aria-label={T.mobileNo[lang]} placeholder={T.mobileHint[lang]} value={phone} onChange={e => setPhone(e.target.value)} className="w100" />
    {!sent ? <button className="w100 mt8" disabled={!agree || phone.length !== 10}
        onClick={() => run(async () => { const r = await api("/auth/request-otp", J({ phone })); if (r.dev_code) setCode(r.dev_code); setSent(true); })}>{T.otpSend[lang]}</button>
      : <><input inputMode="numeric" aria-label={T.otpCode[lang]} placeholder={T.otpCode[lang]} value={code} onChange={e => setCode(e.target.value)} className="w100 mt8" />
        <button className="w100 mt8" onClick={() => run(async () => { await api("/auth/verify-otp", J({ phone, code, consent: agree, language: lang })); onLogin(); })}>{T.send[lang]}</button></>}
    {err && <p className="err">{err}</p>}</div>);
}

function Chat({ fid, lang, onDone }: { fid: string; lang: Lang; onDone: () => void }) {
  const [q, setQ] = useState<{ field?: string; kind?: string; question?: string; done?: boolean; answered?: number; remaining?: number } | null>(null);
  const [text, setText] = useState(""); const [pending, setPending] = useState<any>(null); const [note, setNote] = useState("");
  const [stack, setStack] = useState<string[]>([]); const [listening, setListening] = useState(false); const [live, setLive] = useState(""); const [rec, setRec] = useState<any>(null);
  const t = (k: string) => T[k][lang];
  const load = async () => { const n = await api(`/me/next-question?lang=${lang}`); setQ(n); if (n.question) speak(n.question, lang); };
  useEffect(() => { load(); }, [lang]);
  const submit = async (txt: string) => { if (!q?.field) return; setPending({ ...(await api(`/me/extract`, J({ field: q.field, text: txt }))), original: txt }); };
  const confirm = async (ok: boolean) => {
    if (ok && pending?.value !== null) { await api(`/me/confirm`, J({ field: pending.field, value: pending.value })); setStack(x => [...x, pending.field]); }
    setPending(null); setText(""); load();
  };
  const quick = async (v: boolean | null) => {      // one tap = an explicit answer (null = "I don't know", stored as unknown, never as yes/no)
    if (!q?.field) return; try { await api(`/me/confirm`, J({ field: q.field, value: v })); setStack(x => [...x, q.field as string]); } catch { /* the question simply stays */ }
    setText(""); load();
  };
  const back = async () => { const f = stack[stack.length - 1]; if (!f) return; try { await api(`/me/answers/${f}`, { method: "DELETE" }); setStack(x => x.slice(0, -1)); setPending(null); setText(""); load(); } catch { setNote(t("errorMsg")); } };
  const mic = () => {
    setNote(""); if (listening) { rec?.stop(); return; }
    setLive(""); const r = listen(lang, s => { setText(s); setLive(""); setListening(false); submit(s); }, { onInterim: setLive, onEnd: () => setListening(false) });
    if (!r) setNote(t("voiceUnsupported")); else { setRec(r); setListening(true); }
  };
  if (!q) return <div role="status"><span className="sr">{t("loading")}</span><Skel rows={2} /></div>;
  if (q?.done) { return <div className="card"><p>{t("done")}</p><button onClick={onDone}>{t("results")}</button></div>; }
  const show = (v: unknown) => v === true ? t("yes") : v === false ? t("no") : String(v);
  return (<div>
    {!pending && <Tell lang={lang} onApplied={load} />}
    {q?.remaining !== undefined && <div className="progress"><small role="status">{fill(t("qProgress"), { n: (q.answered ?? 0) + 1, m: (q.answered ?? 0) + q.remaining })}</small><progress className="pg" max={(q.answered ?? 0) + q.remaining} value={q.answered ?? 0} aria-hidden="true" /></div>}
    <div className="card"><b>{q?.question}</b><br /><button className="alt" onClick={() => q?.question && speak(q.question, lang, true)}><Icon n="repeat" /> {t("replay")}</button></div>
    {!pending && q?.kind === "bool" && <div className="row yn" role="group" aria-label={t("quickAnswer")}>
      <button onClick={() => quick(true)}><Icon n="check" /> {t("yes")}</button><button className="alt" onClick={() => quick(false)}><Icon n="cross" /> {t("no")}</button><button className="alt" onClick={() => quick(null)}><Icon n="help" /> {t("dontKnow")}</button></div>}
    {!pending && <>
      <button className={"mic" + (listening ? " listening" : "")} aria-pressed={listening} aria-label={listening ? t("stopListening") : t("speak")} onClick={mic}><Icon n="mic" /></button>
      {listening && <div role="status" className="live"><b>{t("listeningNow")}</b>{live && <div><i>“{live}”</i></div>}<button className="alt mt8" onClick={mic}>{t("stopListening")}</button></div>}
      {note && <p role="alert" className="notice">{note}</p>}
      <div className="row"><input aria-label={t("yourAnswer")} value={text} onChange={e => setText(e.target.value)} /><button onClick={() => submit(text)}>{t("send")}</button></div>
      {stack.length > 0 && <button className="alt mt8" onClick={back}><Icon n="back" /> {t("qBack")}</button>}</>}
    {pending && <div className="card">
      <small>{t("youSaid")}</small><p><i>“{pending.original}”</i></p>
      <small>{t("understood")}</small><p className="big26 my4">{pending.value === null ? "?" : <b>{show(pending.value)}</b>}</p>
      <span className={`badge ${pending.confidence === "high" ? "green" : pending.confidence === "medium" ? "amber" : "red"}`}>{t("conf_" + pending.confidence)}</span>
      {[pending.note && T["note_" + pending.note] ? "note_" + pending.note : null, ...(pending.flags || []).filter((f: string) => T["flag_" + f]).map((f: string) => "flag_" + f)].filter(Boolean).map((k: any) => <p key={k} className="warn-text"><Icon n="warn" /> {t(k)}</p>)}
      {pending.confidence === "low" && !pending.note && <p className="err"><Icon n="warn" /> {t("lowconf")}</p>}
      <p>{t("confirmQ")}</p>
      <div className="row"><button onClick={() => confirm(true)} disabled={pending.value === null}>{t("correct")}</button><button className="alt" onClick={() => { setText(pending.original); setPending(null); }}>{t("change")}</button></div></div>}
  </div>);
}

function DoFirst({ title, name, text }: { title: string; name?: string; text?: string | null }) {     // the single most important line on a result
  return (<div className="dofirst"><span className="step" aria-hidden="true">1</span><div><b>{title}{name ? `: ${name}` : ""}</b>{text && <div>{text}</div>}</div></div>);
}

function Hero({ s, est, lang }: { s: any; est: any; lang: Lang }) {
  const t = (k: string) => T[k][lang];
  const fill = (x: string, o: Record<string, number>) => x.replace(/\{(\w+)\}/g, (_m: string, k: string) => String(o[k] ?? ""));
  const title = s.potential > 0 ? fill(t("heroTitle"), { n: s.potential }) : t("heroNone");
  const sub = s.potential > 0 ? fill(t("heroSplit"), { g: s.green, a: s.amber }) : "";
  const say = [title, sub, s.do_first ? `${t("doFirst")}: ${s.do_first.name}` : ""].filter(Boolean).join(". ");
  return (<div className="card hero" role="region" aria-label={title}>
    <h2 className="m0">{title}</h2>{sub && <p className="my4">{sub}</p>}
    {est?.counted?.length > 0 ? <p><b>{t("estimateTitle")}: ₹{est.annual_inr_if_all_approved}</b><br /><small>{est.note}</small></p> : <small>{t("verifiedPay")}</small>}
    {s.do_first && <DoFirst title={t("doFirst")} name={s.do_first.name} text={s.do_first.step} />}
    <button className="alt mt8"  onClick={() => speak(say, lang)}><Icon n="speaker" /> {t("readAloud")}</button></div>);
}

function ReportRule({ scheme, lang }: { scheme: string; lang: Lang }) {
  const [txt, setTxt] = useState(""); const [done, setDone] = useState(false); const [err, setErr] = useState(false);
  return (<details><summary><small>{T.reportRule[lang]}</small></summary>
    {done ? <p role="status">{T.reportSent[lang]}</p> : <>
      <textarea aria-label={T.reportRule[lang]} placeholder={T.reportPlaceholder[lang]} rows={2} maxLength={500} value={txt} onChange={e => setTxt(e.target.value)} className="w100" />
      <button className="alt" disabled={txt.trim().length < 5} onClick={async () => { setErr(false); try { await api("/me/report-rule", J({ scheme_id: scheme, text: txt.trim() })); setDone(true); } catch { setErr(true); } }}>{T.send[lang]}</button>
      {err && <p className="err">{T.errorMsg[lang]}</p>}</>}</details>);
}

function HelpFinder({ lang }: { lang: Lang }) {   // opens a map search; this is NOT an official list of centres and says so
  const [place, setPlace] = useState("");
  const go = () => window.open("https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent("Common Service Centre " + place.trim()), "_blank", "noopener,noreferrer");
  return (<div className="card"><b><Icon n="building" /> {T.findHelp[lang]}</b>
    <div className="row mt8" ><input aria-label={T.findHelpHint[lang]} placeholder={T.findHelpHint[lang]} value={place} onChange={e => setPlace(e.target.value)} />
      <button disabled={place.trim().length < 3} onClick={go}>{T.findHelpOpen[lang]}</button></div>
    <small>{T.findHelpNote[lang]}</small></div>);
}

function Explain({ trace, lang }: { trace: any[]; lang: Lang }) {
  const t = (k: string) => T[k][lang];
  return (<ul className="pl18">{trace.map((x: any) => (
    <li key={x.rule_id} className="explain-li">
      <Icon n={x.result === "pass" ? "check" : x.result === "fail" ? "cross" : "help"} /> <b>{t(x.result === "pass" ? "matched" : x.result === "fail" ? "notMatched" : "needsConfirm")}</b><br />{x.text}
      {Object.keys(x.reported || {}).length > 0 && <div><small>{t("reported")}: {Object.entries(x.reported).map(([k, v]) => `${k} = ${v === true ? t("yes") : v === false ? t("no") : String(v)}`).join(", ")}</small></div>}
      <div><small>{x.evidence?.length ? x.evidence.map((e: any) => `${e.title}${e.page ? ", p." + e.page : e.section ? ", " + e.section : ""}`).join("; ") : <><Icon n="doc" /> {t("sourcePending")}</>} · {x.rule_id}</small></div></li>))}</ul>);
}

function Ticks({ trace, lang }: { trace: any[]; lang: Lang }) {     // the "why" at a glance: one line per condition, with a word as well as a symbol
  const t = (k: string) => T[k][lang];
  const word = (x: any) => x.result === "unknown" ? t("needsConfirm") : (x.type === "exclude" || x.type === "flag") ? t(x.result === "pass" ? "notExcluded" : "excludedLabel") : t(x.result === "pass" ? "met" : "notMet");
  return (<ul className="ticks">{trace.map((x: any) => <li key={x.rule_id}><span className={`tk ${x.result}`} role="img" aria-label={word(x)}><Icon n={x.result === "pass" ? "check" : x.result === "fail" ? "cross" : "help"} /></span><span>{x.text} <small>· {word(x)}</small></span></li>)}</ul>);
}

const fill = (x: string, o: Record<string, number>) => x.replace(/\{(\w+)\}/g, (_m: string, k: string) => String(o[k] ?? ""));

function Skel({ rows = 3 }: { rows?: number }) {      // placeholder while data loads: never a blank screen
  return (<div className="card skel" aria-hidden="true">{Array.from({ length: rows }, (_, i) => <div key={i} className={"bar b" + (i % 3)} />)}</div>);
}

function Results({ fid, lang }: { fid: string; lang: Lang }) {
  const [d, setD] = useState<any>(null); const [pack, setPack] = useState<string | null>(null); const [err, setErr] = useState(false);
  const t = (k: string) => T[k][lang];
  const load = () => { setErr(false); setD(null); api(`/me/discover`).then(setD).catch(() => setErr(true)); };
  useEffect(() => { load(); }, []);
  if (err) return <div className="card"><p>{t("errorMsg")}</p><button onClick={load}>{t("retry")}</button></div>;
  if (!d) return <div role="status"><span className="sr">{t("loading")}</span><Skel /><Skel /></div>;
  if (d.results.length === 0 && d.members.length === 0) return <div className="card">{t("noSchemes")}</div>;
  return (<div>
    {d.results.some((r: any) => r.rule_status !== "verified") && <div className="notice" role="note"><b><Icon n="warn" /> {t("notVerifiedTitle")}</b><br />{t("notVerifiedBody")}</div>}
    {d.summary && <Hero s={d.summary} est={d.estimate} lang={lang} />}{d.results.map((r: any) => (
    <div className="card" key={r.scheme_id}>
      <b>{r.name}</b> <span className={`badge ${r.status}`}>{t(r.status)}</span>{r.rule_status !== "verified" && <span className="chip">{t("draftChip")}</span>}
      <p className="my6">{r.benefit}</p>
      <Ticks trace={r.trace} lang={lang} />
      {(() => { const m = d.summary?.per_scheme?.[r.scheme_id]; return m?.near_miss ? <p className="notice"><b>{t("nearMiss")}</b> {m.blocked_by[0]}</p> : null; })()}
      {r.status !== "red" && r.application_steps?.length > 0 && <DoFirst title={t("doFirst")} text={r.application_steps[0]} />}
      {r.status !== "red" && <div className="row"><button onClick={() => setPack(r.scheme_id)}>{t("claimPack")}</button><button className="alt" onClick={() => api(`/me/applications`, J({ scheme_id: r.scheme_id }))}>{t("track")}</button></div>}
      <details><summary>{t("seeDetails")}</summary>
        <p><small>{t("meaning_" + r.status)}</small></p>
        <Explain trace={r.trace} lang={lang} />
        <b>{t("docs")}</b><ul>{r.documents.map((x: string) => <li key={x}>{x}</li>)}</ul>
        {r.application_steps?.length > 0 && <details><summary><b>{t("steps")}</b></summary><ol>{r.application_steps.map((x: string) => <li key={x}>{x}</li>)}</ol></details>}
        {r.manual_checks.map((m: string) => <small key={m}><Icon n="warn" /> {m}<br /></small>)}
        <p><b>{t(r.status === "red" ? "finalResultRed" : "finalResult")}</b></p>
        <details><summary><small>{t("details")}</small></summary><small>v{r.version} · {r.last_verified ?? "—"} · <a href={r.source} target="_blank" rel="noreferrer">{r.source}</a>{r.stale_review && <b> · <Icon n="warn" /> {t("stale")}</b>}</small></details>
        <div className="row mt8 col" >
          <a href={r.source} target="_blank" rel="noreferrer"><button className="alt w100" >{t("official")}</button></a>
          {r.status === "red" && <><button className="alt" onClick={() => api(`/me/applications`, J({ scheme_id: r.scheme_id }))}>{t("track")}</button><button className="alt" onClick={() => setPack(r.scheme_id)}>{t("claimPack")}</button></>}</div>
        <ReportRule scheme={r.scheme_id} lang={lang} />
      </details>
    </div>))}{d.members?.length > 0 && <><h3>{t("members")}</h3>{d.members.map((m: any) => <div className="card" key={m.member_id}>
      <b>{m.relationship} · {m.age}</b>{m.results.map((r: any) => <div key={r.scheme_id} className="mt8">{r.name} <span className={`badge ${r.status}`}>{t(r.status)}</span>
        {r.conflicts?.length > 0 && <div><small><Icon n="warn" /> {r.conflicts[0].note}</small></div>}<Explain trace={r.trace} lang={lang} /></div>)}</div>)}</>}
    {pack && <ClaimPack id={pack} lang={lang} onClose={() => setPack(null)} />}
    <HelpFinder lang={lang} />
    <small>{d.disclaimer}</small></div>);
}

function Apps({ fid, lang }: { fid: string; lang: Lang }) {
  const [rows, setRows] = useState<any[] | null>(null); const [err, setErr] = useState(false); const refs = useRef<Record<string, string>>({});
  const load = () => { setErr(false); return api(`/me/applications`).then(setRows).catch(() => setErr(true)); };
  useEffect(() => { load(); }, []);
  const upd = async (id: string, status: string) => { await api(`/me/applications/${id}`, { method: "PATCH", body: JSON.stringify({ status, reference_number: refs.current[id] || "" }) }); load(); };
  if (err) return <div className="card" role="alert"><p>{T.errorMsg[lang]}</p><button onClick={load}>{T.retry[lang]}</button></div>;
  if (rows === null) return <div role="status"><span className="sr">{T.loading[lang]}</span><Skel /><Skel rows={2} /></div>;
  if (rows.length === 0) return <div className="card"><p>{T.noApps[lang]}</p></div>;
  return (<div>{rows.map(a => (<div className="card" key={a.id}>
    <b>{a.scheme_id}</b> — {T["st_" + a.status]?.[lang] ?? a.status} <small>({T.selfrep[lang]})</small> <Timeline key={a.status + a.reference_number} id={a.id} lang={lang} />
    <input aria-label="Ref no." placeholder="Ref no." defaultValue={a.reference_number} onChange={e => (refs.current[a.id] = e.target.value)} />
    <div className="row mt8" >{["prepared", "submitted", "under_review", "approved", "received", "rejected"].map(s => <button key={s} className={(a.status === s ? "" : "alt") + " p8"} onClick={() => upd(a.id, s)}>{T["st_" + s][lang]}</button>)}</div>
  </div>))}</div>);
}

function Family({ lang }: { lang: Lang }) {
  const [rows, setRows] = useState<any[]>([]); const [rel, setRel] = useState("spouse"); const [age, setAge] = useState(""); const [occ, setOcc] = useState(""); const [ok, setOk] = useState(false);
  const [attr, setAttr] = useState<Record<string, string>>({ has_disability: "", is_widowed: "", is_student: "" });
  const tri = (v: string) => (v === "" ? null : v === "yes");
  const [issues, setIssues] = useState<any[]>([]);
  const load = () => { api("/me/family").then(setRows); api("/me/family/issues").then(setIssues); }; useEffect(() => { load(); }, []);
  return (<div><div className="card"><small>{T.famConsent[lang]}</small>
    <div className="row mt8" ><select aria-label="Relationship" value={rel} onChange={e => setRel(e.target.value)}>
      {["spouse", "son", "daughter", "father", "mother", "other"].map(x => <option key={x}>{x}</option>)}</select>
      <input inputMode="numeric" aria-label={T.age[lang]} placeholder={T.age[lang]} value={age} onChange={e => setAge(e.target.value)} /></div>
    <input aria-label="Occupation" className="w100 my8" placeholder="Occupation" value={occ} onChange={e => setOcc(e.target.value)} />
    <div className="row">{(["has_disability", "is_widowed", "is_student"] as const).map(k => <label key={k}><small>{T[{ has_disability: "disability", is_widowed: "widowed", is_student: "student" }[k]][lang]}</small>
      <select value={attr[k]} onChange={e => setAttr(a => ({ ...a, [k]: e.target.value }))} className="w100"><option value="">{T.unknown[lang]}</option><option value="yes">{T.yes[lang]}</option><option value="no">{T.no[lang]}</option></select></label>)}</div>
    <label className="block my8"><input type="checkbox" checked={ok} onChange={e => setOk(e.target.checked)} /> {T.memberConsent[lang]}</label>
    <button disabled={!age} onClick={async () => { await api("/me/family", J({ relationship: rel, age: Number(age), occupation: occ, consent: ok, has_disability: tri(attr.has_disability), is_widowed: tri(attr.is_widowed), is_student: tri(attr.is_student) })); setAge(""); setOcc(""); setOk(false); setAttr({ has_disability: "", is_widowed: "", is_student: "" }); load(); }}>{T.add[lang]}</button></div>
    {rows.map(m => <div className="card" key={m.id}>{m.relationship} · {m.age} {m.occupation && `· ${m.occupation}`} <Icon n={m.consent ? "check" : "pause"} label={m.consent ? T.yes[lang] : T.no[lang]} /></div>)}
    {issues.map((x, i) => <p key={i} className="warn-text"><Icon n="warn" /> {T["issue_" + x.kind]?.[lang] ?? x.kind}</p>)}
    <HelpFinder lang={lang} /><HelpConsent lang={lang} /></div>);
}

function Wallet({ lang }: { lang: Lang }) {
  const [d, setD] = useState<any>(null); const [apps, setApps] = useState<any[]>([]); const [rem, setRem] = useState<any[]>([]);
  const [err, setErr] = useState(false);
  const load = () => { setErr(false); api("/me/discover").then(setD).catch(() => setErr(true)); api("/me/applications").then(setApps).catch(() => {}); api("/me/reminders").then(setRem).catch(() => {}); };
  useEffect(() => { load(); }, []);
  if (err) return <div className="card" role="alert"><p>{T.errorMsg[lang]}</p><button onClick={load}>{T.retry[lang]}</button></div>;
  if (!d) return <div role="status"><span className="sr">{T.loading[lang]}</span><Skel /><Skel rows={2} /></div>;
  const potential = d.results.filter((r: any) => r.status !== "red");
  const count = (s: string) => apps.filter(a => a.status === s).length;
  return (<div>
    <div className="card"><b>{T.potential[lang]}: {potential.length}</b>
      {potential.map((r: any) => <div key={r.scheme_id}>• {r.name} — {r.benefit_detail?.verified ? `₹${r.benefit_detail.amount_inr} / ${r.benefit_detail.frequency}` : <small>{T.amount[lang]}</small>}
        {r.deadline && <small> · <Icon n="clock" /> {r.deadline}</small>}</div>)}</div>
    <div className="card row">{["prepared", "submitted", "approved", "received"].map(s => <div key={s}><b className="big28">{count(s)}</b><br /><small>{T[s][lang]}</small></div>)}</div>
    {d.estimate?.counted?.length > 0 && <div className="card"><b>{T.estimateTitle[lang]}: ₹{d.estimate.annual_inr_if_all_approved}</b><br /><small>{d.estimate.note}</small></div>}
    <small>{T.verifiedPay[lang]}</small>
    {rem.length > 0 && <div className="card"><b>{T.reminders[lang]}</b>{rem.map((x, i) => <div key={i}><Icon n="clock" /> {x.kind === "missing_document" ? `${T.remMissing[lang]}: ${x.doc_type} (${x.scheme_id})` : x.kind === "deadline" ? `${T.remDeadline[lang]}: ${x.scheme_id} ${x.date} (${x.days_left})` : `${T.remExpiring[lang]}: ${x.doc_type} ${x.date}`}</div>)}</div>}
    <small>{d.disclaimer}</small></div>);
}

function DeleteAll({ lang, onDone }: { lang: Lang; onDone: () => void }) {     // never one tap: say what is lost, default focus on the safe choice
  const [ask, setAsk] = useState(false); const [err, setErr] = useState(false);
  if (!ask) return <p className="mt32"><button className="alt danger-text p8 fs15"  onClick={() => setAsk(true)}>{T.deleteAll[lang]}</button></p>;
  return (<div className="card" role="alertdialog" aria-label={T.deleteAsk[lang]}><b>{T.deleteAsk[lang]}</b><p>{T.deleteWarn[lang]}</p>
    <div className="row"><button className="alt" autoFocus onClick={() => { setAsk(false); setErr(false); }}>{T.cancel[lang]}</button>
      <button className="danger" onClick={async () => { setErr(false); try { await api("/me", { method: "DELETE" }); onDone(); } catch { setErr(true); } }}>{T.deleteYes[lang]}</button></div>
    {err && <p role="alert" className="notice">{T.errorMsg[lang]}</p>}</div>);
}

function HelpConsent({ lang }: { lang: Lang }) {
  const [id, setId] = useState(""); const [list, setList] = useState<any[]>([]); const [err, setErr] = useState(false);
  const load = () => api("/me/consents").then(setList); useEffect(() => { load(); }, []);
  return (<div className="card"><b>{T.helper[lang]}</b>
    <div className="row"><input aria-label="Help centre ID" placeholder="Help centre ID" value={id} onChange={e => setId(e.target.value)} />
      <button disabled={!id} onClick={async () => { try { await api("/me/consents", J({ partner_id: id })); setId(""); setErr(false); load(); } catch { setErr(true); } }}>{T.add[lang]}</button></div>
    {err && <p role="alert" className="notice">{T.errorMsg[lang]}</p>}
    {list.map(c => <div key={c.partner_id}>{c.partner_id} <button className="alt p6"  onClick={async () => { await api(`/me/consents/${c.partner_id}`, { method: "DELETE" }); load(); }} aria-label={T.remove[lang]}><Icon n="cross" /></button></div>)}</div>);
}

const FIELD_LABELS: Record<string, string> = { survey_no: "Survey no.", area_acres: "Acres", patta_no: "Patta no.", issue_date: "Issue date (YYYY-MM-DD)", valid_until: "Valid until (YYYY-MM-DD)", income_inr: "Annual income ₹", ifsc: "IFSC" };
const NUMERIC = new Set(["area_acres", "income_inr"]);
function Docs({ lang }: { lang: Lang }) {
  const [type, setType] = useState("land_record"); const [docs, setDocs] = useState<any[] | null>(null); const [msg, setMsg] = useState(""); const [last, setLast] = useState<any>(null); const [dIssues, setDIssues] = useState<any[]>([]);
  const [edit, setEdit] = useState<Record<string, Record<string, string>>>({});
  const load = () => { api("/me/documents").then(setDocs).catch(() => { setDocs(x => x ?? []); setMsg(T.errorMsg[lang]); }); api("/me/documents/issues").then(setDIssues).catch(() => {}); }; useEffect(() => { load(); }, []);
  const upload = async (f: File) => {
    const fd = new FormData(); fd.append("file", f); setMsg("…");
    try { const r = await api(`/me/documents?doc_type=${type}`, { method: "POST", body: fd });
      setLast(r); setMsg((r.ocr_available ? "" : T.ocrNA[lang] + " ") + (r.type_mismatch ? T.mismatch[lang] : "")); load(); } catch (e: any) { setMsg(String(e.message).slice(0, 100)); } };
  const save = async (d: any) => {
    const raw = { ...d.extracted, ...d.confirmed, ...(edit[d.id] || {}) }; const fields: Record<string, any> = {};
    for (const [k, v] of Object.entries(raw)) if (String(v).trim() !== "") fields[k] = NUMERIC.has(k) ? Number(v) : String(v);
    try { await api(`/me/documents/${d.id}/confirm`, J({ fields })); load(); } catch { setMsg(T.errorMsg[lang]); } };
  const fieldsFor: Record<string, string[]> = { land_record: ["survey_no", "area_acres", "patta_no"], income_certificate: ["income_inr", "issue_date", "valid_until"], bank_passbook: ["ifsc"], community_certificate: ["issue_date", "valid_until"] };
  return (<div>
    <div className="row"><select aria-label="Document type" value={type} onChange={e => setType(e.target.value)}>{Object.keys(fieldsFor).map(k => <option key={k}>{k}</option>)}</select>
      <input type="file" aria-label={T.upload[lang]} accept=".pdf,.png,.jpg,.jpeg" capture="environment" onChange={e => e.target.files?.[0] && upload(e.target.files[0])} /></div>
    <small>{T.notAuth[lang]}</small>{msg && <p>{msg}</p>}
    {last?.analysis && <div className="card"><small>{T.detectedAs[lang]}: <b>{last.analysis.detected_type}</b>{last.analysis.detected_type === "unknown" && ` — ${T.notSure[lang]}`}</small>
      {[...(last.analysis.warnings || []), ...(last.quality_warnings || []).map((w: string) => w === "low_resolution" ? "low_resolution" : w)].map((w: string) => <p key={w} className="warn-text my4"><Icon n="warn" /> {T["warn_" + w]?.[lang] ?? (w === "low_resolution" ? T.lowRes[lang] : w)}</p>)}</div>}
    {dIssues.map((x, i) => <p key={i} className="err"><Icon n="warn" /> {x.kind}: {JSON.stringify(x.values ?? [x.document, x.answer])}</p>)}
    {docs === null ? <div role="status"><span className="sr">{T.loading[lang]}</span><Skel /></div> : docs.length === 0 ? <p className="my8"><small>{T.noDocs[lang]}</small></p> : docs.map(d => (<div className="card" key={d.id}><b>{d.doc_type}</b> <Icon n={Object.keys(d.confirmed).length > 0 ? "check" : "help"} />
      {d.checked_by_a_person && <small> <Icon n="user" /> {T.checkedByPerson[lang]}</small>}
      {(fieldsFor[d.doc_type] || []).map(k => <div key={k}><small>{FIELD_LABELS[k]}{last?.analysis?.field_confidence?.[k] === "low" && d.id === last.id ? <b className="err"> <Icon n="warn" /> {T.checkThis[lang]}</b> : null}</small>
        <input aria-label={FIELD_LABELS[k]} className="w100" defaultValue={String(d.confirmed[k] ?? d.extracted[k] ?? "")} onChange={e => setEdit(s => ({ ...s, [d.id]: { ...(s[d.id] || {}), [k]: e.target.value } }))} /></div>)}
      <div className="row mt8" ><button onClick={() => save(d)}>{T.saveFields[lang]}</button>
        {d.doc_type === "land_record" && d.confirmed.area_acres != null && <button className="alt" onClick={() => api("/me/confirm", J({ field: "land_owned_acres", value: d.confirmed.area_acres, overwrite: true }))}>{T.useLand[lang]}</button>}</div></div>))}</div>);
}

function Tell({ lang, onApplied }: { lang: Lang; onApplied: () => void }) {
  const [text, setText] = useState(""); const [props, setProps] = useState<any[]>([]); const [busy, setBusy] = useState(false); const [voiceErr, setVoiceErr] = useState(false);
  const show = (v: unknown) => v === true ? T.yes[lang] : v === false ? T.no[lang] : String(v);
  const go = async () => { setBusy(true); try { setProps((await api("/me/chat", J({ text }))).proposals); } finally { setBusy(false); } };
  const apply = async (p: any) => { await api("/me/confirm", J({ field: p.field, value: p.value, overwrite: true })); setProps(x => x.filter(y => y.field !== p.field)); onApplied(); };
  return (<details className="card"><summary><b>{T.tell[lang]}</b></summary>
    <div className="row mt8" ><input aria-label={T.tell[lang]} value={text} onChange={e => setText(e.target.value)} /><button disabled={!text || busy} onClick={go}>{T.send[lang]}</button>
      <button className="alt" aria-label={T.speak[lang]} onClick={() => { setVoiceErr(false); if (!listen(lang, setText)) setVoiceErr(true); }}><Icon n="mic" /></button></div>
    {voiceErr && <p role="alert" className="notice">{T.voiceUnsupported[lang]}</p>}
    {props.map(p => <div key={p.field} className="mt8"><b>{p.field}: {show(p.value)}</b>
      {p.note === "contradicts_earlier_answer" && <small className="err"> <Icon n="warn" /> {T.contradicts[lang]} ({show(p.previous)})</small>}
      {p.confidence === "low" && p.note !== "contradicts_earlier_answer" && <small className="err"> <Icon n="warn" /> {T.lowconf[lang]}</small>}
      <div className="row"><button onClick={() => apply(p)}>{T.apply[lang]}</button><button className="alt" onClick={() => setProps(x => x.filter(y => y.field !== p.field))}>{T.skip[lang]}</button></div></div>)}</details>);
}

function ClaimPack({ id, lang, onClose }: { id: string; lang: Lang; onClose: () => void }) {
  const [p, setP] = useState<any>(null);
  useEffect(() => { api(`/me/claim-pack/${id}`).then(setP).catch(() => onClose()); }, []);
  if (!p) return null;
  return (<div className="pack bigprint card"><h2>{p.scheme.name}</h2>
    {p.scheme.rule_status === "verified" ? <p><small><Icon n="check" /> {T.verifiedOn[lang]}: {p.scheme.last_verified} · v{p.scheme.version} · {p.generated_at}</small></p>
      : <div className="notice"><b><Icon n="warn" /> {T.notVerifiedTitle[lang]}</b><br />{T.notVerifiedBody[lang]}<br /><small>v{p.scheme.version} · {p.generated_at}</small></div>}
    <p>{p.scheme.benefit}</p>
    <h3>{T.docs[lang]}</h3><ul>{p.document_checklist.map((x: any) => <li key={x.doc_type}><Icon n={x.uploaded ? (x.details_confirmed ? "check" : "dot") : "box"} /> {x.doc_type}</li>)}{p.other_documents.map((x: string) => <li key={x}><Icon n="box" /> {x}</li>)}</ul>
    <h3>{T.steps[lang]}</h3><ol>{p.steps.map((x: string) => <li key={x}>{x}</li>)}</ol>
    <h3><Icon n="check" /> / <Icon n="cross" /></h3><Explain trace={p.trace} lang={lang} />
    {p.manual_checks.map((m: string) => <p key={m}><small><Icon n="warn" /> {m}</small></p>)}
    <h3>{T.lvRules[lang]} / {T.lvDocs[lang]} / {T.lvPerson[lang]} / {T.lvOfficial[lang]}</h3>
    <ul className="nolist"><li><Icon n={p.assurance.rules_matched ? "check" : "box"} /> {T.lvRules[lang]}</li><li><Icon n={p.assurance.documents_supplied.length ? "check" : "box"} /> {T.lvDocs[lang]}: {p.assurance.documents_supplied.join(", ") || "—"}</li>
      <li><Icon n={p.assurance.documents_checked_by_a_person.length ? "check" : "box"} /> {T.lvPerson[lang]}</li><li><Icon n="box" /> {T.lvOfficial[lang]} — <small>{p.assurance.officially_confirmed_note}</small></li></ul>
    {p.timeline?.current && <><h3>{T.history[lang]}</h3><ol className="nolist">{p.timeline.steps.map((x: any) => <li key={x.id}><Icon n={x.reached ? "check" : "box"} /> {T["tl_" + x.id][lang]}{x.date && ` · ${x.date}`}</li>)}</ol><small>{T.tlSelf[lang]}</small></>}
    <h3>{T.tracking[lang]}</h3>{p.tracking.length === 0 ? <small>—</small> : p.tracking.map((x: any, i: number) => <div key={i}>{x.status} {x.reference_number && `· ${x.reference_number}`} · {x.updated}</div>)}
    {p.qr_svg && <div><img alt="QR" width={120} height={120} src={"data:image/svg+xml;utf8," + encodeURIComponent(p.qr_svg)} /><br /><small>{T.scanOfficial[lang]}</small></div>}
    <p><a href={p.scheme.source} target="_blank" rel="noreferrer">{p.scheme.source}</a></p><p><small>{p.disclaimer}</small></p>
    <div className="row noprint"><button onClick={() => window.print()}>{T.print[lang]}</button><button className="alt" onClick={onClose}>{T.close[lang]}</button></div></div>);
}

function Timeline({ id, lang }: { id: string; lang: Lang }) {
  const [t, setT] = useState<any>(null);
  return (<details onToggle={e => { if ((e.target as HTMLDetailsElement).open) api(`/me/applications/${id}/timeline`).then(setT).catch(() => setT(null)); }}><summary>{T.history[lang]}</summary>
    {t && <div><ol className="nolist">{t.steps.map((x: any) => <li key={x.id} className="mb6"><Icon n={x.reached ? "check" : "box"} /> <b>{T["tl_" + x.id][lang]}</b>{x.date && ` · ${x.date}`}{x.reached && <><br /><small>{T.tlSelf[lang]}</small></>}</li>)}</ol>
      {t.reference_number && <small>Ref: {t.reference_number}</small>}<br /><small>{t.disclaimer}</small></div>}</details>);
}
