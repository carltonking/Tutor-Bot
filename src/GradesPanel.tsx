import { useEffect, useState } from "react";
type G = { title:string; score:number; max:number; topics:string };

const inputStyle = { background:"#1A1A1E", border:"1px solid #2A2A2E", borderRadius:8, padding:"8px 10px", color:"white", fontSize:12 } as const;

export function GradesPanel({ subjectId, onChanged }: { subjectId:string; onChanged?: () => void }) {
  const [grades, setGrades] = useState<G[]>([]);
  const [title, setTitle] = useState("");
  const [score, setScore] = useState("");
  const [max, setMax] = useState("100");
  const [topics, setTopics] = useState("");
  useEffect(()=>{ fetch(`http://localhost:1421/grades/${subjectId}`).then(r=>r.json()).then(setGrades).catch(()=>{}); },[subjectId]);
  async function add(){
    if(!title.trim() || !score.trim()) return;
    const maxN = parseFloat(max) || 100;
    const fd = new FormData(); fd.append("title",title); fd.append("score",score); fd.append("max",String(maxN)); fd.append("topics",topics);
    try{ await fetch(`http://localhost:1421/grades/${subjectId}`,{method:"POST", body:fd}); }catch{}
    setGrades(g=>[...g,{title, score:parseFloat(score), max:maxN, topics}]);
    setTitle(""); setScore(""); setTopics("");
    // Mastery writeback + plan re-pace happen server-side; refresh the panels
    onChanged?.();
  }
  return (
    <div style={{display:"flex", flexDirection:"column", gap:8}}>
      <div className="panel-title">Log real grade (hybrid topic mapping)</div>
      <input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Exam title" style={inputStyle} />
      <div style={{display:"flex", gap:6}}>
        <input value={score} onChange={e=>setScore(e.target.value)} placeholder="Score" style={{...inputStyle, flex:1}} />
        <input value={max} onChange={e=>setMax(e.target.value)} placeholder="Max" style={{...inputStyle, width:64}} />
      </div>
      <input value={topics} onChange={e=>setTopics(e.target.value)} placeholder="Topics: e.g. derivatives, integrals" style={inputStyle} />
      <button className="u-btn" onClick={add} disabled={!title.trim() || !score.trim()}>Add Grade</button>
      {grades.map((g,i)=>(
        <div key={i} className="file">
          {g.title} — {g.score}/{g.max}
          <span>{g.topics || "no topics"} · {g.max>0 && g.score/g.max<0.8 ? "needs remediation" : "passing"}</span>
        </div>
      ))}
      <div className="file"><span>Mastery updates per topic (80% on last two grades = mastered); weak topics are added to the plan automatically.</span></div>
      <div className="file"><span>To auto-sync grades, ask the Main Agent: "connect my grades".</span></div>
    </div>
  );
}
