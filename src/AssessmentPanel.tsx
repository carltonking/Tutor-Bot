import { useState } from "react";
type Q = { id:string; type:string; prompt:string; topic:string; citation:string; rubric:string };
type MasteryHint = { topic:string; score_last2:number; mastery:boolean };

export function AssessmentPanel({ subjectId, onMasteryChange }: { subjectId:string; onMasteryChange?: () => void }) {
  const [qs, setQs] = useState<Q[]>([]);
  const [answers, setAnswers] = useState<Record<string,string>>({});
  const [grades, setGrades] = useState<Record<string,{score:number; reasoning:string; mastery?: MasteryHint}>>({});
  const [loading, setLoading] = useState(false);
  const [topicHint, setTopicHint] = useState("");

  async function gen() {
    setLoading(true);
    try {
      const fd = new FormData(); fd.append("subject_id", subjectId); fd.append("count","5");
      if (topicHint.trim()) fd.append("topic", topicHint.trim());
      const r = await fetch("http://localhost:1421/assess/generate",{method:"POST", body: fd});
      const j = await r.json(); setQs(j.questions||[]);
    } catch { setQs([{id:"mock1",type:"mcq",prompt:"Mock: What is a limit?",topic: topicHint || "general",citation:"Syllabus p1",rubric:"Correct definition"}]); }
    setLoading(false);
  }

  async function grade(id:string) {
    const q = qs.find(x=>x.id===id)!; const ans = answers[id]||"";
    try {
      const fd = new FormData();
      fd.append("prompt", q.prompt);
      fd.append("answer", ans);
      fd.append("rubric", q.rubric);
      fd.append("subject_id", subjectId);
      fd.append("topic", q.topic || topicHint || "general");
      const r = await fetch("http://localhost:1421/assess/grade",{method:"POST", body: fd});
      const j = await r.json();
      setGrades(g=>({...g,[id]:{score:j.score,reasoning:j.reasoning, mastery: j.mastery}}));
      onMasteryChange?.();
    } catch { setGrades(g=>({...g,[id]:{score:60,reasoning:"Mock grade"}})); }
  }

  return (
    <div style={{display:"flex",flexDirection:"column",gap:10}}>
      <input
        placeholder="Topic focus (optional)"
        value={topicHint}
        onChange={e=>setTopicHint(e.target.value)}
        style={{background:"#1A1A1E", border:"1px solid #2A2A2E", borderRadius:8, padding:"8px 10px", color:"white", fontSize:12}}
      />
      <button className="u-btn" onClick={gen} disabled={loading}>{loading?"Generating...":"+ Generate 5 Questions (teacher-style)"}</button>
      {qs.map(q=>(
        <div key={q.id} className="file" style={{gap:8}}>
          <div style={{fontSize:13, fontWeight:600}}>{q.type==="mcq"?"MCQ":"Short"} — {q.topic} <span style={{fontWeight:400, color:"#9A9AA0"}}>· {q.citation.slice(0,40)}...</span></div>
          <div style={{fontSize:13}}>{q.prompt}</div>
          <div style={{fontSize:11, color:"#9A9AA0"}}>Rubric: {q.rubric}</div>
          <input placeholder="Your answer" value={answers[q.id]||""} onChange={e=>setAnswers(a=>({...a,[q.id]:e.target.value}))} style={{background:"#1A1A1E", border:"1px solid #2A2A2E", borderRadius:8, padding:"8px 10px", color:"white", fontSize:12}} />
          <button className="u-btn" onClick={()=>grade(q.id)}>Grade</button>
          {grades[q.id] && (
            <div style={{fontSize:12}}>
              Score: <b>{grades[q.id].score}%</b> — {grades[q.id].reasoning}{" "}
              {grades[q.id].mastery && (
                <span style={{color:"#9A9AA0"}}>
                  · mastery {grades[q.id].mastery!.topic}: {Math.round(grades[q.id].mastery!.score_last2)}%
                  {grades[q.id].mastery!.mastery ? " ✓" : ""}
                </span>
              )}
              <button className="u-btn" onClick={()=>grade(q.id)} style={{marginLeft:6}}>Re-grade (dispute)</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
