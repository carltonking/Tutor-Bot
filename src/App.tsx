import { useCallback, useEffect, useRef, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { MemoryPanel } from "./MemoryPanel";
import { AssessmentPanel } from "./AssessmentPanel";
import { GradesPanel } from "./GradesPanel";
import {
  SearchIcon, PlusIcon, BotIcon, PencilIcon,
  DotsIcon, GearIcon, LogoutIcon, AttachIcon, AppleIcon, GoogleIcon,
} from "./Icons";
import "./App.css";

const SIDECAR = "http://localhost:1421";
const SESSION_KEY = "tutorbot.session";
const QUEUE_KEY = "tutorbot.pending";

type User = { name: string; email: string };
type Row = { id: string; name: string; color: string };
type Msg = { role: "user" | "bot" | "system"; text?: string; media?: boolean };
type PlanItem = { week: number; topic: string; status: string; week_of?: string | null };
type MasteryRow = { topic: string; score_last: number | null; score_prev: number | null; mastery_bool: boolean; updated_at?: string };
type Onboarding = { objective: string; mode: "course" | "self"; school: string; course_code: string; start_date: string; end_date: string };
const EMPTY_ONBOARDING: Onboarding = { objective: "", mode: "self", school: "", course_code: "", start_date: "", end_date: "" };
// Offline queue: mutations made while the sidecar is down, replayed on next load
type Pending =
  | { type: "create"; row: Row }
  | { type: "rename"; id: string; name: string }
  | { type: "delete"; id: string }
  | { type: "message"; subjectId: string; role: string; text: string };

function loadQueue(): Pending[] {
  try { return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]"); } catch { return []; }
}
function saveQueue(q: Pending[]) {
  try { localStorage.setItem(QUEUE_KEY, JSON.stringify(q)); } catch { /* private mode */ }
}
function enqueue(p: Pending) {
  const q = loadQueue();
  q.push(p);
  saveQueue(q);
}

const PALETTE = ["#e14b4b", "#e91e8c", "#f07f13", "#3b82f6", "#22c55e", "#a855f7", "#f5a623"];

const LEAD = "Lead agent";
const LEAD_ID = "main";

const SEED_CHAT: Msg[] = [
  { role: "bot", text: "I'm the Lead agent. Tell me what you're studying and I'll spin up a tutor for each subject." },
  { role: "bot", text: "I can also sync your grades — just say \"connect my grades\"." },
];

const tutorName = (name: string) => `${name} tutor`;

function AgentAvatar({ size = 36 }: { size?: number }) {
  return (
    <span className="row-avatar" style={{ width: size, height: size }}>
      <BotIcon size={Math.round(size * 0.5)} />
    </span>
  );
}

function MediaCard() {
  return (
    <div className="media-wrap">
      <div className="media-card">
        <div className="media-head">
          <div>
            <div className="media-balance-label">Balance</div>
            <div className="media-balance-row">
              <span className="media-balance">$0.00</span>
              <span className="chip-green">⌃ 39.30</span>
              <span className="chip-green">0.00%</span>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#b5b5b5" strokeWidth="2" style={{ display: "block" }}><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></svg>
            </div>
          </div>
          <div className="media-actions"><span>Deposit</span><span>Withdraw</span></div>
        </div>
        <div className="media-chart">
          <svg viewBox="0 0 560 86" preserveAspectRatio="none">
            <path d="M0,70 L40,68 L80,71 L120,66 L160,69 L200,63 L240,66 L280,58 L320,61 L360,52 L400,55 L440,40 L480,44 L520,20 L560,8 L560,86 L0,86 Z" fill="#fdf3d1" />
            <path d="M0,70 L40,68 L80,71 L120,66 L160,69 L200,63 L240,66 L280,58 L320,61 L360,52 L400,55 L440,40 L480,44 L520,20 L560,8" fill="none" stroke="#f0c94a" strokeWidth="2" />
          </svg>
          <span className="media-nodata">No Data</span>
        </div>
        <div className="media-foot">
          <div className="media-cell">
            <div><div className="media-cell-label">Crypto</div><div className="media-cell-value">$0.00</div></div>
            <span className="media-cell-btn">Browse Crypto ›</span>
          </div>
          <div className="media-cell">
            <div><div className="media-cell-label">Rewards</div><div className="media-cell-value">$0.00</div></div>
            <span className="media-cell-btn">Stake Now ›</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function LoginScreen({ onLogin }: { onLogin: (u: User) => void }) {
  return (
    <div className="login">
      <div className="login-card">
        <div className="login-logo"><BotIcon size={40} /></div>
        <h1 className="login-title">Tutor Bot</h1>
        <p className="login-sub">Your personal tutor for every subject.</p>
        <button className="login-btn apple" onClick={() => onLogin({ name: "Carlton King", email: "carlton@icloud.com" })}>
          <AppleIcon size={18} /> Continue with Apple
        </button>
        <button className="login-btn google" onClick={() => onLogin({ name: "Carlton King", email: "carlton.king@gmail.com" })}>
          <GoogleIcon size={18} /> Continue with Google
        </button>
        <p className="login-note">Nothing leaves your machine except to your chosen LLM provider.</p>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<User | null>(() => {
    try { return JSON.parse(localStorage.getItem(SESSION_KEY) || "null"); } catch { return null; }
  });
  const [rows, setRows] = useState<Row[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [selected, setSelected] = useState<string>(LEAD_ID);
  const [query, setQuery] = useState("");
  const [input, setInput] = useState("");
  const [chatLog, setChatLog] = useState<Record<string, Msg[]>>({});
  const [typing, setTyping] = useState(false);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameVal, setRenameVal] = useState("");
  const [rowMenuId, setRowMenuId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Row | null>(null);
  const [newSubject, setNewSubject] = useState<string | null>(null);
  const [onboarding, setOnboarding] = useState<Onboarding>(EMPTY_ONBOARDING);
  const [profileMenu, setProfileMenu] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);
  const [tab, setTab] = useState<"Sources" | "Plan" | "Mastery" | "Memory" | "Assessment">("Sources");
  const [sources, setSources] = useState<Array<{ id: string; filename: string; type: string; pages: number; chunks: number }>>([]);
  const [plan, setPlan] = useState<PlanItem[]>([]);
  const [planLoading, setPlanLoading] = useState(false);
  const [mastery, setMastery] = useState<MasteryRow[]>([]);
  const chatRef = useRef<HTMLDivElement>(null);

  const refreshPlan = useCallback((id: string) => {
    fetch(`${SIDECAR}/plan/${id}`).then((r) => r.json()).then((j) => setPlan(Array.isArray(j) ? j : [])).catch(() => setPlan([]));
  }, []);
  const refreshMastery = useCallback((id: string) => {
    fetch(`${SIDECAR}/mastery/${id}`).then((r) => r.json()).then((j) => setMastery(Array.isArray(j) ? j : [])).catch(() => setMastery([]));
  }, []);
  async function regeneratePlan(id: string) {
    setPlanLoading(true);
    try {
      const fd = new FormData();
      const row = rows.find((r) => r.id === id);
      const name = row?.name ?? "";
      fd.append("objective", name);
      await fetch(`${SIDECAR}/plan/generate/${id}`, { method: "POST", body: fd });
    } catch { /* offline — plan tab will show empty */ }
    refreshPlan(id);
    setPlanLoading(false);
  }

  // Load plan + mastery for the selected agent
  useEffect(() => {
    if (!user || selected === LEAD_ID) { setPlan([]); setMastery([]); return; }
    refreshPlan(selected);
    refreshMastery(selected);
  }, [user, selected, refreshPlan, refreshMastery]);

  // Load agents from DB, then replay any mutations made while offline
  useEffect(() => {
    if (!user) return;
    fetch(`${SIDECAR}/subjects`).then((r) => r.json()).then(async (j: Array<{ id: string; name: string; color: string }>) => {
      let base: Row[] = Array.isArray(j)
        ? j.map((s, i) => ({ id: s.id, name: s.name, color: s.color || PALETTE[i % PALETTE.length] }))
        : [];
      // Replay offline queue against the sidecar
      const q = loadQueue();
      const remaining: Pending[] = [];
      for (const op of q) {
        try {
          if (op.type === "create") {
            const fd = new FormData();
            fd.append("name", op.row.name);
            fd.append("color", op.row.color);
            const r = await fetch(`${SIDECAR}/subjects`, { method: "POST", body: fd });
            const created = await r.json();
            if (created.id) {
              base = base.map((x) => (x.id === op.row.id ? { ...created, color: op.row.color } : x));
              if (!base.some((x) => x.id === created.id)) base = [...base, { id: created.id, name: op.row.name, color: op.row.color }];
              if (selected === op.row.id) setSelected(created.id);
            }
          } else if (op.type === "rename") {
            const fd = new FormData();
            fd.append("name", op.name);
            await fetch(`${SIDECAR}/subjects/${op.id}`, { method: "PATCH", body: fd });
          } else if (op.type === "delete") {
            await fetch(`${SIDECAR}/subjects/${op.id}`, { method: "DELETE" });
            base = base.filter((x) => x.id !== op.id);
          } else if (op.type === "message") {
            const fd = new FormData();
            fd.append("role", op.role);
            fd.append("text", op.text);
            await fetch(`${SIDECAR}/messages/${op.subjectId}`, { method: "POST", body: fd });
          }
        } catch {
          remaining.push(op); // still offline — keep for next time
        }
      }
      saveQueue(remaining);
      setRows(base);
      setLoaded(true);
    }).catch(() => {
      // Sidecar down on boot: hydrate from the offline queue so nothing is lost
      const q = loadQueue();
      let rows: Row[] = [];
      for (const op of q) {
        if (op.type === "create") rows = rows.some((x) => x.id === op.row.id) ? rows : [...rows, op.row];
        if (op.type === "rename") rows = rows.map((x) => (x.id === op.id ? { ...x, name: op.name } : x));
        if (op.type === "delete") rows = rows.filter((x) => x.id !== op.id);
      }
      setRows(rows);
      setLoaded(true);
    });
  }, [user]);

  // Load persisted conversation for the selected agent
  useEffect(() => {
    if (!user) return;
    fetch(`${SIDECAR}/messages/${selected}`).then((r) => r.json()).then((j: Array<{ role: string; text: string }>) => {
      if (Array.isArray(j) && j.length) {
        setChatLog((c) => ({ ...c, [selected]: j.map((m) => ({ role: m.role as Msg["role"], text: m.text })) }));
      } else if (selected === LEAD_ID) {
        setChatLog((c) => ({ ...c, [LEAD_ID]: SEED_CHAT }));
      } else {
        setChatLog((c) => ({ ...c, [selected]: [] }));
      }
    }).catch(() => {
      setChatLog((c) => ({ ...c, [selected]: selected === LEAD_ID ? SEED_CHAT : [] }));
    });
  }, [selected, user]);

  useEffect(() => {
    fetch(`${SIDECAR}/sources/${selected === LEAD_ID ? "chieff" : selected}`).then((r) => r.json()).then(setSources).catch(() => setSources([]));
  }, [selected, user]);

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight });
  }, [chatLog, typing, selected]);

  const log = chatLog[selected] ?? [];
  const activeRow = rows.find((r) => r.id === selected);
  const activeName = selected === LEAD_ID ? LEAD : tutorName(activeRow?.name ?? "");
  const filtered = rows.filter((r) => tutorName(r.name).toLowerCase().includes(query.toLowerCase()));

  const pushMsg = useCallback((id: string, m: Msg, persist = true) => {
    setChatLog((c) => ({ ...c, [id]: [...(c[id] ?? []), m] }));
    if (persist && m.text) {
      const fd = new FormData();
      fd.append("role", m.role);
      fd.append("text", m.text);
      fetch(`${SIDECAR}/messages/${id}`, { method: "POST", body: fd }).catch(() => {
        enqueue({ type: "message", subjectId: id, role: m.role, text: m.text! });
      });
    }
  }, []);

  async function send() {
    const text = input.trim();
    if (!text) return;
    setInput("");
    // /chat persists both sides of the exchange — don't double-save the user turn
    pushMsg(selected, { role: "user", text }, false);
    setTyping(true);
    try {
      const fd = new FormData();
      fd.append("subject_id", selected);
      fd.append("message", text);
      const r = await fetch(`${SIDECAR}/chat`, { method: "POST", body: fd });
      const j = await r.json();
      // /chat persists both sides itself — don't double-save the bot reply
      setChatLog((c) => ({ ...c, [selected]: [...(c[selected] ?? []), { role: "bot", text: j.answer || "(empty response)" }] }));
    } catch {
      enqueue({ type: "message", subjectId: selected, role: "user", text });
      pushMsg(selected, { role: "bot", text: "(sidecar offline — message saved and will sync when it's back)" }, false);
    } finally {
      setTyping(false);
    }
  }

  async function attachFiles() {
    let paths: string | string[] | null = null;
    try {
      paths = await open({
        multiple: true,
        filters: [{ name: "Documents", extensions: ["pdf", "txt", "md", "docx", "png", "jpg", "jpeg"] }],
      });
    } catch {
      paths = null;
    }
    if (!paths) return;
    const list = Array.isArray(paths) ? paths : [paths];
    for (const p of list) {
      const filename = String(p).split("/").pop() || "file";
      pushMsg(selected, { role: "system", text: `Attached ${filename}` });
      try {
        const blob = await fetch(`file://${p}`).then((r) => r.blob());
        const fd = new FormData();
        fd.append("file", blob, filename);
        fd.append("subject_id", selected);
        fd.append("file_type", "attachment");
        const r = await fetch(`${SIDECAR}/ingest`, { method: "POST", body: fd });
        const j = await r.json();
        if (j.id) {
          setSources((s) => [...s, { id: j.id, filename: j.filename ?? filename, type: "attachment", pages: j.pages ?? 0, chunks: j.chunks ?? 0 }]);
          pushMsg(selected, { role: "bot", text: `Indexed ${filename} — ${j.chunks ?? 0} chunks ready.` });
        } else {
          pushMsg(selected, { role: "bot", text: `Attached ${filename} — couldn't index (${j.error ?? "unsupported format"}).` });
        }
      } catch {
        pushMsg(selected, { role: "bot", text: `Attached ${filename} (sidecar offline — not indexed).` }, false);
      }
    }
  }

  async function createSubject(name: string) {
    const color = PALETTE[rows.length % PALETTE.length];
    const fallbackRow: Row = { id: String(Date.now()), name, color };
    try {
      const fd = new FormData();
      fd.append("name", name);
      fd.append("color", color);
      fd.append("objective", onboarding.objective);
      fd.append("mode", onboarding.mode);
      if (onboarding.mode === "course") {
        fd.append("school", onboarding.school);
        fd.append("course_code", onboarding.course_code);
      }
      fd.append("start_date", onboarding.start_date);
      fd.append("end_date", onboarding.end_date);
      const r = await fetch(`${SIDECAR}/subjects`, { method: "POST", body: fd });
      const j = await r.json();
      if (j.id) {
        setRows((rs) => [...rs, { id: j.id, name, color }]);
        setSelected(j.id);
        setNewSubject(null);
        return;
      }
      enqueue({ type: "create", row: fallbackRow });
    } catch {
      enqueue({ type: "create", row: fallbackRow });
    }
    setRows((rs) => [...rs, fallbackRow]);
    setSelected(fallbackRow.id);
    setNewSubject(null);
    setOnboarding(EMPTY_ONBOARDING);
  }

  function startRename(id: string) {
    const row = rows.find((r) => r.id === id);
    if (!row) return;
    setRenaming(id);
    setRenameVal(row.name);
    setRowMenuId(null);
  }

  async function commitRename() {
    const id = renaming;
    const name = renameVal.trim();
    setRenaming(null);
    if (!id || !name) return;
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, name } : r)));
    try {
      const fd = new FormData();
      fd.append("name", name);
      await fetch(`${SIDECAR}/subjects/${id}`, { method: "PATCH", body: fd });
    } catch {
      enqueue({ type: "rename", id, name });
    }
  }

  async function deleteAgent(row: Row) {
    setRows((rs) => rs.filter((r) => r.id !== row.id));
    setChatLog((c) => {
      const n = { ...c };
      delete n[row.id];
      return n;
    });
    setConfirmDelete(null);
    setRowMenuId(null);
    if (selected === row.id) setSelected(LEAD_ID);
    try {
      await fetch(`${SIDECAR}/subjects/${row.id}`, { method: "DELETE" });
    } catch {
      enqueue({ type: "delete", id: row.id });
    }
  }

  async function uploadSource(type: string) {
    const p = await open({ multiple: false, filters: [{ name: "PDF", extensions: ["pdf"] }] });
    if (!p) return;
    const filename = String(p).split("/").pop() || "file.pdf";
    try {
      const blob = await fetch(`file://${p}`).then((r) => r.blob());
      const fd = new FormData();
      fd.append("file", blob, filename);
      fd.append("subject_id", selected);
      fd.append("file_type", type);
      const r = await fetch(`${SIDECAR}/ingest`, { method: "POST", body: fd });
      const j = await r.json();
      if (j.id) {
        setSources((s) => [...s, { id: j.id, filename: j.filename ?? filename, type, pages: j.pages ?? 0, chunks: j.chunks ?? 0 }]);
        if (selected !== LEAD_ID) { refreshPlan(selected); refreshMastery(selected); }
      }
    } catch {
      setSources((s) => [...s, { id: String(Date.now()), filename, type, pages: 0, chunks: 0 }]);
    }
  }

  function login(u: User) {
    setUser(u);
    try { localStorage.setItem(SESSION_KEY, JSON.stringify(u)); } catch { /* private mode */ }
  }

  function logout() {
    setUser(null);
    try { localStorage.removeItem(SESSION_KEY); } catch { /* ignore */ }
    setSelected(LEAD_ID);
  }

  if (!user) return <LoginScreen onLogin={login} />;

  return (
    <div className="app">
      {/* ===== Sidebar ===== */}
      <aside className="sidebar">
        <div className="search-wrap">
          <span className="search-icon"><SearchIcon size={15} /></span>
          <input className="search" placeholder="Search" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>

        <div className="featured" onClick={() => setSelected(LEAD_ID)}>
          <div className="featured-avatar"><BotIcon size={44} /></div>
          <div className="featured-name">{LEAD}</div>
        </div>

        <div className="subject-list">
          {filtered.map((r) => (
            <div
              key={r.id}
              className={`row ${selected === r.id ? "selected" : ""}`}
              onClick={() => { if (renaming !== r.id) setSelected(r.id); }}
            >
              <AgentAvatar />
              <div className="row-text">
                {renaming === r.id ? (
                  <input
                    className="row-name-input"
                    autoFocus
                    value={renameVal}
                    onChange={(e) => setRenameVal(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") commitRename();
                      if (e.key === "Escape") setRenaming(null);
                    }}
                    onBlur={commitRename}
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <span className="row-name">{tutorName(r.name)}</span>
                )}
              </div>
              <button
                className="row-dots"
                title="Agent options"
                onClick={(e) => { e.stopPropagation(); setRowMenuId(rowMenuId === r.id ? null : r.id); }}
              >
                <DotsIcon size={15} className="dots-vertical" />
              </button>
              {rowMenuId === r.id && (
                <div className="menu row-menu" onClick={(e) => e.stopPropagation()}>
                  <button className="menu-item" onClick={() => startRename(r.id)}>
                    <PencilIcon size={14} /> Rename
                  </button>
                  <button className="menu-item danger" onClick={() => { setConfirmDelete(r); setRowMenuId(null); }}>
                    <LogoutIcon size={14} className="icon-flip-h" /> Delete agent
                  </button>
                </div>
              )}
            </div>
          ))}
          {!filtered.length && loaded && <div className="row-empty">No tutors yet — create one</div>}
        </div>

        <button className="new-subject-btn" onClick={() => setNewSubject("")}>
          <PlusIcon size={15} /> New tutor
        </button>

        {/* ===== Profile footer ===== */}
        <div className="profile-row">
          <button className="profile">
            <span className="profile-badge">{user.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}</span>
            <span className="profile-meta">
              <span className="profile-name">{user.name}</span>
              <span className="profile-email">{user.email}</span>
            </span>
          </button>
          <button className="profile-dots" title="Account options" onClick={() => setProfileMenu((v) => !v)}>
            <DotsIcon size={16} />
          </button>
          {profileMenu && (
            <div className="menu profile-menu">
              <button className="menu-item" onClick={() => { setProfileMenu(false); setSettingsOpen(true); }}>
                <GearIcon size={14} /> User settings
              </button>
              <button className="menu-item" onClick={logout}>
                <LogoutIcon size={14} /> Log out
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* ===== Center ===== */}
      <main className="center">
        <header className="header header-centered">
          <AgentAvatar size={30} />
          <span className="header-name">{activeName}</span>
        </header>

        <div className="chat" ref={chatRef}>
          {log.map((m, i) =>
            m.media ? <MediaCard key={i} /> : m.role === "system" ? (
              <div key={i} className="system-line">{m.text}</div>
            ) : (
              <div key={i} className={`bubble ${m.role}`}>{m.text}</div>
            ),
          )}
          {typing && <div className="typing"><i /><i /><i /></div>}
        </div>

        <div className="input-bar">
          <div className="input-pill">
            <button className="plus-btn" title="Attach files" onClick={attachFiles}><PlusIcon size={18} /></button>
            <input
              className="chat-input"
              placeholder={`Message ${activeName}`}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") send(); }}
            />
            <button className="attach-btn" title="Attach files" onClick={attachFiles}><AttachIcon size={16} /></button>
          </div>
        </div>
      </main>

      {/* ===== Right inspector (Study App panels) ===== */}
      {rightOpen && (
        <aside className="inspector">
          <div className="tabs">
            {(["Sources", "Plan", "Mastery", "Memory", "Assessment"] as const).map((t) => (
              <span key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>{t}</span>
            ))}
          </div>
          <div className="inspector-body">
            {tab === "Sources" && (
              <>
                <div className="panel-title">Sources (per subject)</div>
                <div className="upload-row">
                  <button className="u-btn" onClick={() => uploadSource("syllabus")}>+ Syllabus</button>
                  <button className="u-btn" onClick={() => uploadSource("textbook")}>+ Textbook</button>
                  <button className="u-btn" onClick={() => uploadSource("teacher_notes")}>+ Notes</button>
                  <button className="u-btn" onClick={() => uploadSource("practice_problems")}>+ Problems</button>
                </div>
                {sources.map((f) => (
                  <div key={f.id} className="file">{f.filename} <span>{f.type} · {f.pages} pages · {f.chunks} chunks</span></div>
                ))}
                {!sources.length && <div className="file"><span>No sources yet — upload a syllabus or textbook PDF.</span></div>}
              </>
            )}
            {tab === "Plan" && (
              <>
                <div className="plan-head">
                  <div className="panel-title">Semester Plan</div>
                  <button className="u-btn" onClick={() => regeneratePlan(selected)} disabled={planLoading}>{planLoading ? "…" : "Regenerate"}</button>
                </div>
                {plan.map((p) => (
                  <div key={p.week} className={p.status === "active" ? "week active" : "week"}>
                    <span>Week {p.week}{p.week_of ? ` · ${p.week_of}` : ""}</span>
                    <span className="week-topic">{p.topic}</span>
                  </div>
                ))}
                {!plan.length && !planLoading && (
                  <div className="file"><span>No plan yet. Set start/end dates and click Regenerate.</span></div>
                )}
                <hr />
                <GradesPanel subjectId={selected} onChanged={() => { refreshPlan(selected); refreshMastery(selected); }} />
              </>
            )}
            {tab === "Mastery" && (
              <>
                <div className="panel-title">Mastery</div>
                {mastery.map((m) => (
                  <div key={m.topic} className="bar">
                    <span>{m.topic} {m.mastery_bool ? "· mastered" : m.score_last != null && m.score_last < 0.8 ? "· needs remediation" : ""}</span>
                    <div className="track"><div className={m.mastery_bool ? "fill" : "fill weak"} style={{ width: `${Math.round((m.score_last ?? 0) * 100)}%` }} /></div>
                  </div>
                ))}
                {!mastery.length && <div className="file"><span>No mastery data yet — log grades or take assessments.</span></div>}
              </>
            )}
            {tab === "Memory" && <MemoryPanel subjectId={selected} subjectName={activeName} />}
            {tab === "Assessment" && <AssessmentPanel subjectId={selected} />}
          </div>
        </aside>
      )}

      {/* ===== New subject onboarding modal ===== */}
      {newSubject !== null && (
        <div className="overlay" onClick={() => setNewSubject(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>New tutor</h3>
            <input
              autoFocus
              placeholder="Subject name (e.g. Calculus II)"
              value={newSubject}
              onChange={(e) => setNewSubject(e.target.value)}
            />
            <input
              placeholder="Objective — what do you want to master? (optional)"
              value={onboarding.objective}
              onChange={(e) => setOnboarding({ ...onboarding, objective: e.target.value })}
            />
            <div className="form-row">
              <div className="seg">
                <span className={onboarding.mode === "course" ? "seg-btn active" : "seg-btn"} onClick={() => setOnboarding({ ...onboarding, mode: "course" })}>Course</span>
                <span className={onboarding.mode === "self" ? "seg-btn active" : "seg-btn"} onClick={() => setOnboarding({ ...onboarding, mode: "self" })}>Self-learning</span>
              </div>
            </div>
            {onboarding.mode === "course" && (
              <div className="form-row two">
                <input placeholder="School (optional)" value={onboarding.school} onChange={(e) => setOnboarding({ ...onboarding, school: e.target.value })} />
                <input placeholder="Course code" value={onboarding.course_code} onChange={(e) => setOnboarding({ ...onboarding, course_code: e.target.value })} />
              </div>
            )}
            <div className="form-row two">
              <label className="date-field"><span>Start date</span><input type="date" value={onboarding.start_date} onChange={(e) => setOnboarding({ ...onboarding, start_date: e.target.value })} /></label>
              <label className="date-field"><span>End date</span><input type="date" value={onboarding.end_date} onChange={(e) => setOnboarding({ ...onboarding, end_date: e.target.value })} /></label>
            </div>
            <div className="settings-note">With dates set, a week-by-week plan is generated for the whole range.</div>
            <div className="modal-actions">
              <button className="btn-ghost" onClick={() => setNewSubject(null)}>Cancel</button>
              <button className="btn-primary" disabled={!newSubject.trim()} onClick={() => createSubject(newSubject.trim())}>Create</button>
            </div>
          </div>
        </div>
      )}

      {/* ===== Delete confirm modal ===== */}
      {confirmDelete && (
        <div className="overlay" onClick={() => setConfirmDelete(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Delete "{tutorName(confirmDelete.name)}"?</h3>
            <div className="settings-note">
              This permanently removes the agent, its conversation, sources, and memory. This cannot be undone.
            </div>
            <div className="modal-actions">
              <button className="btn-ghost" onClick={() => setConfirmDelete(null)}>Cancel</button>
              <button className="btn-danger" onClick={() => deleteAgent(confirmDelete)}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* ===== Settings modal ===== */}
      {settingsOpen && (
        <div className="overlay" onClick={() => setSettingsOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>User settings</h3>
            <input value={user.name} readOnly />
            <input value={user.email} readOnly />
            <div className="settings-note">
              Tutor Bot v0.1.0 · LLM provider keys are stored in your OS keychain.
              Nothing leaves your machine except to your chosen provider.
            </div>
            <div className="modal-actions">
              <button className="btn-primary" onClick={() => setSettingsOpen(false)}>Done</button>
            </div>
          </div>
        </div>
      )}

      {/* click-away for menus */}
      {(profileMenu || rowMenuId) && (
        <div style={{ position: "fixed", inset: 0, zIndex: 50 }} onClick={() => { setProfileMenu(false); setRowMenuId(null); }} />
      )}

      {/* inspector toggle (keyboard: Cmd/Ctrl+I) */}
      <KeyboardToggle onToggle={() => setRightOpen((v) => !v)} />
    </div>
  );
}

function KeyboardToggle({ onToggle }: { onToggle: () => void }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "i") { e.preventDefault(); onToggle(); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onToggle]);
  return null;
}
