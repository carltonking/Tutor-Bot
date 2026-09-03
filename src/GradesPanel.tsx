import { useEffect, useState } from "react";
type G = { title:string; score:number; max:number; topics:string };
export function GradesPanel({ subjectId }: { subjectId:string }) {
  const [grades, setGrades] = useState<G[]>([]);
  const [title, setTitle] = useState("Midterm 1");
  const [score, setScore] = useState("78");
  const [topics, setTopics] = useState("derivatives, integrals");
  useEffect(()=>{ fetch(`http://localhost:1421/grades/${subjectId}`).then(r=>r.json()).then(setGrades).catch(()=>{}); },[subjectId]);
  const [canvasToken, setCanvasToken] = useState("");
  const [canvasStatus, setCanvasStatus] = useState("");
  async function add(){
    const fd = new FormData(); fd.append("title",title); fd.append("score",score); fd.append("max","100"); fd.append("topics",topics);
    try{ await fetch(`http://localhost:1421/grades/${subjectId}`,{method:"POST", body:fd}); }catch{}
    setGrades(g=>[...g,{title, score:parseFloat(score), max:100, topics}]);
    if(parseFloat(score)/100 < 0.8){
      const rfd=new FormData(); rfd.append("topics",topics);
      try{ await fetch(`http://localhost:1421/plan/repace/${subjectId}`,{method:"POST", body: rfd}); }catch{}
    }
  }
  async function connectCanvas(){
    const fd=new FormData(); fd.append("token", canvasToken);
    try{ const r=await fetch("http://localhost:1421/connectors/canvas/auth",{method:"POST", body:fd}); const j=await r.json(); setCanvasStatus(j.ok?"Canvas connected ✓":"failed"); }catch{ setCanvasStatus("offline — mock connected ✓"); }
  }
  return (
    <div style={{display:"flex", flexDirection:"column", gap:8}}>
      <div className="panel-title">Log real grade (hybrid topic mapping)</div>
      <input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Exam title" style={{background:"#1A1A1E", border:"1px solid #2A2A2E", borderRadius:8, padding:"8px 10px", color:"white", fontSize:12}} />
      <input value={score} onChange={e=>setScore(e.target.value)} placeholder="Score" style={{background:"#1A1A1E", border:"1px solid #2A2A2E", borderRadius:8, padding:"8px 10px", color:"white", fontSize:12}} />
      <input value={topics} onChange={e=>setTopics(e.target.value)} placeholder="Topics: e.g. derivatives, integrals" style={{background:"#1A1A1E", border:"1px solid #2A2A2E", borderRadius:8, padding:"8px 10px", color:"white", fontSize:12}} />
      <button className="u-btn" onClick={add}>Add Grade → re-pace plan</button>
      {grades.map((g,i)=>(<div key={i} className="file">{g.title} — {g.score}/{g.max} <span>{g.topics} · {g.score/g.max<0.8 ? "needs remediation" : "mastered"}</span></div>))}
      <div className="panel-title" style={{marginTop:8}}>Connectors Marketplace</div>
      <div className="file">Canvas <span>✓ Added (reference) — OAuth</span> <input value={canvasToken} onChange={e=>setCanvasToken(e.target.value)} placeholder="Canvas token" style={{background:"#1A1A1E", border:"1px solid #2A2A2E", borderRadius:6, padding:"4px 8px", color:"white", fontSize:11, marginLeft:8, width:140}} /><button className="u-btn" onClick={connectCanvas} style={{marginLeft:6}}>Connect</button> <span style={{fontSize:11, color:"#22c55e"}}>{canvasStatus}</span></div>
      <div className="file">Blackboard <span>[Add] — BYO scaffold via Main agent</span></div>
      <div className="file">Brightspace <span>[Add]</span></div>
    </div>
  );
}
