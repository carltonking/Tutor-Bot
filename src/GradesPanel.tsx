import { useEffect, useState } from "react";
type G = { title:string; score:number; max:number; topics:string };
export function GradesPanel({ subjectId }: { subjectId:string }) {
  const [grades, setGrades] = useState<G[]>([]);
  const [title, setTitle] = useState("Midterm 1");
  const [score, setScore] = useState("78");
  const [topics, setTopics] = useState("derivatives, integrals");
  useEffect(()=>{ fetch(`http://localhost:1421/grades/${subjectId}`).then(r=>r.json()).then(setGrades).catch(()=>{}); },[subjectId]);
  async function add(){
    const fd = new FormData(); fd.append("title",title); fd.append("score",score); fd.append("max","100"); fd.append("topics",topics);
    try{ await fetch(`http://localhost:1421/grades/${subjectId}`,{method:"POST", body:fd}); }catch{}
    setGrades(g=>[...g,{title, score:parseFloat(score), max:100, topics}]);
  }
  return (
    <div style={{display:"flex", flexDirection:"column", gap:8}}>
      <div className="panel-title">Log real grade (hybrid topic mapping)</div>
      <input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Exam title" style={{background:"#1A1A1E", border:"1px solid #2A2A2E", borderRadius:8, padding:"8px 10px", color:"white", fontSize:12}} />
      <input value={score} onChange={e=>setScore(e.target.value)} placeholder="Score" style={{background:"#1A1A1E", border:"1px solid #2A2A2E", borderRadius:8, padding:"8px 10px", color:"white", fontSize:12}} />
      <input value={topics} onChange={e=>setTopics(e.target.value)} placeholder="Topics: e.g. derivatives, integrals" style={{background:"#1A1A1E", border:"1px solid #2A2A2E", borderRadius:8, padding:"8px 10px", color:"white", fontSize:12}} />
      <button className="u-btn" onClick={add}>Add Grade → re-pace plan</button>
      {grades.map((g,i)=>(<div key={i} className="file">{g.title} — {g.score}/{g.max} <span>{g.topics} · {g.score/g.max<0.8 ? "needs remediation" : "mastered"}</span></div>))}
      <div className="panel-title" style={{marginTop:8}}>Connectors Marketplace (stub)</div>
      <div className="file">Canvas <span>✓ Added (reference) — OAuth</span></div>
      <div className="file">Blackboard <span>[Add] — BYO scaffold via Main agent</span></div>
      <div className="file">Brightspace <span>[Add]</span></div>
    </div>
  );
}
