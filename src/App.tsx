import { useState } from "react";
import "./App.css";

type Subject = { id: string; name: string; color: string; time: string; preview: string; initials: string };

const SUBJECTS: Subject[] = [
  { id: "main", name: "Main", initials: "MA", color: "#14b8a6", time: "Yesterday", preview: "ready to spawn your next subject agent..." },
  { id: "calc", name: "Calculus II", initials: "CA", color: "#f97316", time: "8:54 AM", preview: "Done. Midterm 1 → 78% · 2 topics to remediate" },
  { id: "bio", name: "Bio 101", initials: "BI", color: "#a855f7", time: "5:51 AM", preview: "Syllabus parsed → 12 topics · 842 chunks indexed" },
  { id: "cs", name: "Data Structures", initials: "DS", color: "#3b82f6", time: "3:51 AM", preview: "invite's out to vicky. globex note ..." },
  { id: "phys", name: "Physics I", initials: "PH", color: "#22c55e", time: "12:51 AM", preview: "3 practice sets drafted in teacher's style..." },
  { id: "chem", name: "Organic Chem", initials: "OC", color: "#eab308", time: "4:51 AM", preview: "report filed. 9 sources, nothing o..." },
];

function Droplet({ color, initials }: { color: string; initials: string }) {
  return (
    <div className="avatar" style={{ background: color }}>
      <span className="avatar-eyes">¨</span>
      <span className="avatar-text">{initials}</span>
    </div>
  );
}

export default function App() {
  const [selected, setSelected] = useState<string>("calc");
  const [input, setInput] = useState("");
  const [rightOpen, setRightOpen] = useState(true);
  const active = SUBJECTS.find((s) => s.id === selected) || SUBJECTS[0];

  return (
    <div className="app">
      {/* Left */}
      <aside className="sidebar">
        <div className="traffic">
          <span className="dot red" /><span className="dot yellow" /><span className="dot green" />
          <button className="new-btn" title="New Subject">+</button>
        </div>
        <div className="search-wrap">
          <input className="search" placeholder="Search" />
        </div>
        <div className="subject-list">
          {SUBJECTS.map((s) => (
            <button
              key={s.id}
              className={`row ${selected === s.id ? "selected" : ""}`}
              onClick={() => setSelected(s.id)}
            >
              <Droplet color={s.color} initials={s.initials} />
              <div className="row-text">
                <div className="row-top"><span className="row-name">{s.name}</span><span className="row-time">{s.time}</span></div>
                <div className="row-preview">{s.preview}</div>
              </div>
            </button>
          ))}
        </div>
        <div className="profile"><span className="profile-badge">AS</span> Armand Segall</div>
      </aside>

      {/* Center */}
      <main className="center">
        <header className="header">
          <Droplet color={active.color} initials={active.initials} />
          <span className="header-name">{active.name}</span>
          <span className="header-spacer" />
          <button className="icon-btn" onClick={() => setRightOpen((v) => !v)} title="Toggle inspector">{rightOpen ? ">>" : "<<"}</button>
        </header>

        <div className="chat">
          {/* Status stack card — GrokBot pattern */}
          <div className="status-card">
            <div className="status-line"><span className="check">✓</span><b>Syllabus</b> → parsed · 12 topics</div>
            <div className="status-line"><span className="check">✓</span><b>Textbook</b> → indexed · 842 chunks</div>
            <div className="status-line"><span className="check">✓</span><b>Teacher notes</b> → 3 docs · style cloned</div>
            <div className="status-line"><span className="check">✓</span><b>Practice</b> → 36 questions queued · 0 sent</div>
          </div>

          <div className="separator"><span>Messages from <span className="pill purple">Main</span> and <span className="pill teal">{active.name}</span></span></div>

          <div className="bubble bot">
            <span className="pill purple">Main</span> sent over the midterm scope and <span className="pill teal">{active.name}</span> flagged the weak topics. Both are folded into tonight's plan.
          </div>
          <div className="bubble bot">
            The 36 questions are sitting in the practice queue on my screen: topic, style, and a Draft badge on each. Nothing goes out until you've had a look.
          </div>
          <div className="bubble user">The top 10 look good. Send it. Run this every week. <span className="reaction">👍</span></div>
          <div className="system-line">Created routine <span className="clock">🕒</span> Weekly review</div>
          <div className="done-pill">Done.</div>
        </div>

        <div className="input-bar">
          <button className="plus-btn">+</button>
          <input className="chat-input" placeholder={`Message ${active.name}`} value={input} onChange={(e) => setInput(e.target.value)} />
          <button className="mic-btn">🎤</button>
        </div>
      </main>

      {/* Right inspector */}
      {rightOpen && (
        <aside className="inspector">
          <div className="tabs">
            <span className="tab active">Sources</span><span className="tab">Plan</span><span className="tab">Mastery</span><span className="tab">Memory</span>
          </div>
          <div className="inspector-body">
            <div className="panel-title">Sources (per subject)</div>
            <div className="file">Syllabus.pdf <span>12 pages · indexed</span></div>
            <div className="file">Textbook Ch 1-4.pdf <span>842 chunks</span></div>
            <div className="file">Teacher Notes — Stokes.pdf <span>style exemplar</span></div>
            <div className="file">Practice Exam 1.pdf <span>style exemplar</span></div>
            <hr />
            <div className="panel-title">Semester Plan</div>
            <div className="week">Week 1 — Limits <span>✓</span></div>
            <div className="week active">Week 2 — Derivatives <span>●</span></div>
            <div className="week">Week 3 — Integrals <span>○</span></div>
            <hr />
            <div className="panel-title">Mastery</div>
            <div className="bar"><span>Derivatives</span><div className="track"><div className="fill" style={{ width: "62%" }} /></div></div>
            <div className="bar"><span>Integrals</span><div className="track"><div className="fill" style={{ width: "41%" }} /></div></div>
          </div>
        </aside>
      )}
    </div>
  );
}
