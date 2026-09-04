import { useState } from "react";

type Q = { id: string; assessment_id?: string; type: string; prompt: string; topic: string; citation: string; rubric: string };
type GradeInfo = { score: number; reasoning: string; topic?: string; via?: string };

const SIDECAR = "http://localhost:1421";

export function AssessmentPanel({ subjectId, onChanged }: { subjectId: string; onChanged?: () => void }) {
  const [qs, setQs] = useState<Q[]>([]);
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [grades, setGrades] = useState<Record<string, GradeInfo>>({});
  const [loading, setLoading] = useState(false);
  const [offline, setOffline] = useState(false);

  async function gen() {
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("subject_id", subjectId);
      fd.append("count", "5");
      fd.append("kind", "quiz");
      const r = await fetch(`${SIDECAR}/assess/generate`, { method: "POST", body: fd });
      const j = await r.json();
      setQs(j.questions || []);
      setAssessmentId(j.assessment_id || null);
      setOffline(false);
    } catch {
      // sidecar offline: local mock so the UI stays usable
      setOffline(true);
      setAssessmentId(null);
      setQs([{ id: "mock1", type: "mcq", prompt: "Mock: What is a limit?", topic: "Limits", citation: "Syllabus p1", rubric: "Correct definition" }]);
    }
    setLoading(false);
  }

  async function grade(id: string) {
    const q = qs.find((x) => x.id === id);
    if (!q) return;
    const ans = answers[id] || "";
    if (offline || !assessmentId) {
      // offline mock grading — nothing persisted
      setGrades((g) => ({ ...g, [id]: { score: 60, reasoning: "Mock grade (sidecar offline)" } }));
      return;
    }
    try {
      const fd = new FormData();
      fd.append("assessment_id", assessmentId);
      fd.append("question_id", q.id);
      fd.append("subject_id", subjectId);
      fd.append("prompt", q.prompt);
      fd.append("answer", ans);
      fd.append("rubric", q.rubric);
      fd.append("topic", q.topic || "");
      const r = await fetch(`${SIDECAR}/assess/grade`, { method: "POST", body: fd });
      const j = await r.json();
      setGrades((g) => ({ ...g, [id]: { score: j.score, reasoning: j.reasoning, topic: j.topic, via: j.via } }));
      // quiz scores feed mastery + plan re-pace server-side — refresh those panels
      onChanged?.();
    } catch {
      setGrades((g) => ({ ...g, [id]: { score: 0, reasoning: "Grading failed — is the sidecar running?" } }));
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <button className="u-btn" onClick={gen} disabled={loading}>
        {loading ? "Generating..." : "+ Generate 5 Questions (teacher-style)"}
      </button>
      {offline && <div style={{ fontSize: 11, color: "#9A9AA0" }}>Sidecar offline — questions/grades won't be saved.</div>}
      {qs.map((q) => (
        <div key={q.id} className="file" style={{ gap: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>
            {q.type === "mcq" ? "MCQ" : "Short"} — {q.topic}{" "}
            <span style={{ fontWeight: 400, color: "#9A9AA0" }}>· {q.citation.slice(0, 40)}...</span>
          </div>
          <div style={{ fontSize: 13 }}>{q.prompt}</div>
          <div style={{ fontSize: 11, color: "#9A9AA0" }}>Rubric: {q.rubric}</div>
          <input
            placeholder="Your answer"
            value={answers[q.id] || ""}
            onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
            style={{ background: "#1A1A1E", border: "1px solid #2A2A2E", borderRadius: 8, padding: "8px 10px", color: "white", fontSize: 12 }}
          />
          <button className="u-btn" onClick={() => grade(q.id)}>Grade</button>
          {grades[q.id] && (
            <div style={{ fontSize: 12 }}>
              Score: <b>{grades[q.id].score}%</b>
              {grades[q.id].topic && <span style={{ color: "#9A9AA0" }}> · topic: {grades[q.id].topic}</span>}
              {grades[q.id].via && <span style={{ color: "#9A9AA0" }}> · {grades[q.id].via}</span>}
              {" — "}
              {grades[q.id].reasoning}{" "}
              <button className="u-btn" onClick={() => grade(q.id)} style={{ marginLeft: 6 }}>
                Re-grade (dispute)
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
