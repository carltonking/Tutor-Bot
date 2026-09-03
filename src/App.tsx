import { useState, useEffect } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { MemoryPanel } from "./MemoryPanel";
import { AssessmentPanel } from "./AssessmentPanel";
import { GradesPanel } from "./GradesPanel";
// invoke reserved for future Rust commands
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

type Src = { id:string; filename:string; type:string; pages:number; chunks:number };

export default function App() {
  const [selected, setSelected] = useState<string>("calc");
  const [input, setInput] = useState("");
  const [rightOpen, setRightOpen] = useState(true);
  const [sources, setSources] = useState<Src[]>([]);
  const [tab, setTab] = useState<"Sources"|"Plan"|"Mastery"|"Memory"|"Assessment">("Sources");
  const active = SUBJECTS.find((s) => s.id === selected) || SUBJECTS[0];
  const [chatLog, setChatLog] = useState<Array<{role:"user"|"bot", text:string}>>([]);

  useEffect(()=>{
    // fetch sources from python sidecar if running, else mock
    fetch(`http://localhost:1421/sources/${selected}`).then(r=>r.json()).then(setSources).catch(()=> setSources([
      {id:"1",filename:"Syllabus.pdf",type:"syllabus",pages:12,chunks:8},
      {id:"2",filename:"Textbook Ch 1-4.pdf",type:"textbook",pages:42,chunks:842},
    ]));
  },[selected]);

  async function upload(type:string) {
    const p = await open({ multiple:false, filters:[{name:"PDF",extensions:["pdf"]}]});
    if(!p) return;
    // try sidecar ingest
    try {
      const fd = new FormData();
      const blob = await fetch(`file://${p}`).then(r=>r.blob()).catch(()=>null);
      // fallback: Tauri fs read + upload via invoke not yet; show mock
      if(!blob) throw new Error("no blob");
      fd.append("file", blob, String(p).split("/").pop()!);
      fd.append("subject_id", selected);
      fd.append("file_type", type);
      const res = await fetch("http://localhost:1421/ingest", {method:"POST", body: fd});
      const j = await res.json();
      if(j.id) setSources(s=>[...s,{id:j.id,filename:j.filename,type,pages:j.pages,chunks:j.chunks}]);
    } catch {
      // mock add
      setSources(s=>[...s,{id:String(Date.now()),filename:String(p).split("/").pop()||"file.pdf",type,pages:10,chunks:41}]);
    }
  }

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
          <div style={{display:"flex", gap:6, marginBottom:8}}><button className="u-btn" onClick={()=> setChatLog(c=>[...c,{role:"bot",text:"[Assessment] Open inspector → Assessment tab"}])}>Study</button><button className="u-btn" onClick={()=> setTab("Memory")}>Memory</button></div>

          {chatLog.length===0 ? (
            <>
              <div className="bubble bot"><span className="pill purple">Main</span> sent over the midterm scope and <span className="pill teal">{active.name}</span> flagged the weak topics. Both are folded into tonight's plan.</div>
              <div className="bubble bot">The 36 questions are sitting in the practice queue on my screen: topic, style, and a Draft badge on each. Nothing goes out until you've had a look.</div>
              <div className="bubble user">The top 10 look good. Send it. Run this every week. <span className="reaction">👍</span></div>
              <div className="system-line">Created routine <span className="clock">🕒</span> Weekly review</div>
              <div className="done-pill">Done.</div>
            </>
          ) : chatLog.map((m,i)=> m.role==="user" ? <div key={i} className="bubble user">{m.text}</div> : <div key={i} className="bubble bot">{m.text}</div>)}
        </div>

        <div className="input-bar">
          <button className="plus-btn">+</button>
          <input className="chat-input" placeholder={`Message ${active.name}`} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={async (e)=>{ if(e.key==="Enter" && input.trim()){ const u=input; setInput(""); setChatLog(c=>[...c,{role:"user",text:u}]); try{ const r=await fetch(`http://localhost:1421/search/${selected}?q=${encodeURIComponent(u)}&k=2`); const j=await r.json(); const cite=j[0]?.text?.slice(0,120)||"no sources yet — upload PDFs"; setChatLog(c=>[...c,{role:"bot",text:`(${active.name} — citing: "${cite}...") Here's the grounded answer.`}]);}catch{ setChatLog(c=>[...c,{role:"bot",text:`Noted for ${active.name}. (sidecar offline — mock)`}]); } } }} />
          <button className="mic-btn" onClick={async ()=>{ if(!input.trim()) return; const u=input; setInput(""); setChatLog(c=>[...c,{role:"user",text:u}]); try{ const r=await fetch(`http://localhost:1421/search/${selected}?q=${encodeURIComponent(u)}&k=2`); const j=await r.json(); const cite=j[0]?.text?.slice(0,120)||"no sources yet"; setChatLog(c=>[...c,{role:"bot",text:`(${active.name} — citing: "${cite}...") Here's the answer.`}]);}catch{ setChatLog(c=>[...c,{role:"bot",text:`Noted.`}]); } }}>➤</button>
        </div>
      </main>

      {/* Right inspector */}
      {rightOpen && (
        <aside className="inspector">
          <div className="tabs">
            {(["Sources","Plan","Mastery","Memory","Assessment"] as const).map(t=>(
              <span key={t} className={`tab ${tab===t?"active":""}`} onClick={()=>setTab(t as any)}>{t}</span>
            ))}
          </div>
          <div className="inspector-body">
            {tab==="Sources" && (<>
            <div className="panel-title">Sources (per subject) — per ADR 010/013</div>
            <div className="upload-row">
              <button className="u-btn" onClick={()=>upload("syllabus")}>+ Syllabus</button>
              <button className="u-btn" onClick={()=>upload("textbook")}>+ Textbook</button>
              <button className="u-btn" onClick={()=>upload("teacher_notes")}>+ Notes</button>
              <button className="u-btn" onClick={()=>upload("practice_problems")}>+ Problems</button>
            </div>
            {sources.map(f=>(
              <div key={f.id} className="file">{f.filename} <span>{f.type} · {f.pages} pages · {f.chunks} chunks</span></div>
            ))}
            </>)} 
            {tab==="Memory" && <MemoryPanel subjectId={selected} subjectName={active.name} />}
            {tab==="Assessment" && <AssessmentPanel subjectId={selected} />}
            {tab==="Plan" && <GradesPanel subjectId={selected} />}
            {tab!=="Sources" && tab!=="Memory" && tab!=="Assessment" && <div className="panel-title">{tab} (next ticket)</div>}
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
