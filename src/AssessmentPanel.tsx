import { useState, useEffect, useRef } from "react";

type Q = { id: string; assessment_id?: string; type: string; prompt: string; topic: string; citation: string; rubric: string };
type GradeInfo = { score: number; reasoning: string; topic?: string; via?: string };
type TopicRow = { topic: string; score_last: number; score_prev: number | null; mastery_bool: boolean };
type Summary = { overall: number; perTopic: Record<string, { total: number; n: number }>; mastery: TopicRow[] };

const SIDECAR = "http://localhost:1421";
const EXAM_SECONDS = 45 * 60;

export function AssessmentPanel({ subjectId, onChanged }: { subjectId: string; onChanged?: () => void }) {
  const [mode, setMode] = useState<"quiz" | "practice_exam">("quiz");
  const [qs, setQs] = useState<Q[]>([]);
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [grades, setGrades] = useState<Record<string, GradeInfo>>({});
  const [loading, setLoading] = useState(false);
  const [offline, setOffline] = useState(false);
  // exam state
  const [secondsLeft, setSecondsLeft] = useState(EXAM_SECONDS);
  const [paused, setPaused] = useState(false);
  const [current, setCurrent] = useState(0); // exam: which question is open
  const [summary, setSummary] = useState<Summary | null>(null);
  const summaryRef = useRef<HTMLDivElement | null>(null);

  const isExam = mode === "practice_exam";

  // soft countdown for exams (honor-system; never locks submit)
  useEffect(() => {
    if (!isExam || paused || summary || !assessmentId) return;
    if (secondsLeft <= 0) return;
    const t = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [isExam, paused, summary, assessmentId, secondsLeft]);

  const mm = String(Math.floor(Math.max(0, secondsLeft) / 60)).padStart(2, "0");
  const ss = String(Math.max(0, secondsLeft) % 60).padStart(2, "0");

  async function gen() {
    setLoading(true);
    setSummary(null);
    setGrades({});
    setAnswers({});
    setCurrent(0);
    try {
      const fd = new FormData();
      fd.append("subject_id", subjectId);
      fd.append("kind", mode);
      if (mode === "quiz") fd.append("count", "5");
      const r = await fetch(`${SIDECAR}/assess/generate`, { method: "POST", body: fd });
      const j = await r.json();
      setQs(j.questions || []);
      setAssessmentId(j.assessment_id || null);
      setOffline(false);
    } catch {
      setOffline(true);
      setAssessmentId(null);
      setQs([{ id: "mock1", type: "mcq", prompt: "Mock: What is a limit?", topic: "Limits", citation: "Syllabus p1", rubric: "Correct definition" }]);
    }
    if (mode === "practice_exam") {
      setSecondsLeft(EXAM_SECONDS);
      setPaused(false);
    }
    setLoading(false);
  }

  function buildSummary(finalGrades: Record<string, GradeInfo>, mastery: TopicRow[]) {
    const perTopic: Record<string, { total: number; n: number }> = {};
    let total = 0, n = 0;
    for (const q of qs) {
      const g = finalGrades[q.id];
      if (!g) continue;
      const t = g.topic || q.topic || "general";
      perTopic[t] = perTopic[t] || { total: 0, n: 0 };
      perTopic[t].total += g.score;
      perTopic[t].n += 1;
      total += g.score;
      n += 1;
    }
    setSummary({ overall: n ? Math.round(total / n) : 0, perTopic, mastery });
    setTimeout(() => summaryRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  }

  async function refreshMasteryAndSummarize(finalGrades: Record<string, GradeInfo>) {
    try {
      const r = await fetch(`${SIDECAR}/mastery/${subjectId}`);
      const j = await r.json();
      buildSummary(finalGrades, Array.isArray(j) ? j : []);
    } catch {
      buildSummary(finalGrades, []);
    }
  }

  async function grade(id: string) {
    const q = qs.find((x) => x.id === id);
    if (!q) return;
    const ans = answers[id] || "";
    if (offline || !assessmentId) {
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
      const next = { ...grades, [id]: { score: j.score, reasoning: j.reasoning, topic: j.topic, via: j.via } };
      setGrades(next);
      onChanged?.();
      // exam: auto-advance and summarize once every question is scored
      if (isExam) {
        const idx = qs.findIndex((x) => x.id === id);
        const allDone = qs.every((x) => next[x.id]);
        if (allDone) await refreshMasteryAndSummarize(next);
        else setCurrent(Math.min(idx + 1, qs.length - 1));
      }
    } catch {
      setGrades((g) => ({ ...g, [id]: { score: 0, reasoning: "Grading failed — is the sidecar running?" } }));
    }
  }

  function finishExam() {
    const finalGrades = { ...grades };
    // unscored answers get graded (teacher-mode grade-all); empty answers score 0 locally
    const unanswered = qs.filter((q) => !finalGrades[q.id]);
    if (unanswered.length === 0) {
      refreshMasteryAndSummarize(finalGrades);
      return;
    }
    // grade each remaining question sequentially through the real grader
    (async () => {
      let next = finalGrades;
      for (const q of unanswered) {
        const ans = answers[q.id] || "";
        if (offline || !assessmentId) {
          next = { ...next, [q.id]: { score: ans ? 60 : 0, reasoning: ans ? "Mock grade (sidecar offline)" : "No answer" } };
          continue;
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
          next = { ...next, [q.id]: { score: j.score, reasoning: j.reasoning, topic: j.topic, via: j.via } };
          onChanged?.();
        } catch {
          next = { ...next, [q.id]: { score: 0, reasoning: "Grading failed" } };
        }
      }
      setGrades(next);
      await refreshMasteryAndSummarize(next);
    })();
  }

  function reset() {
    setQs([]);
    setAssessmentId(null);
    setAnswers({});
    setGrades({});
    setSummary(null);
    setCurrent(0);
  }

  const gradedCount = qs.filter((q) => grades[q.id]).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="seg">
        <div className={`seg-btn ${mode === "quiz" ? "active" : ""}`} onClick={() => { setMode("quiz"); reset(); }}>Quiz</div>
        <div className={`seg-btn ${mode === "practice_exam" ? "active" : ""}`} onClick={() => { setMode("practice_exam"); reset(); }}>Practice exam</div>
      </div>

      {!assessmentId && !qs.length && (
        <button className="u-btn" onClick={gen} disabled={loading}>
          {loading ? "Generating..." : isExam ? "+ Generate practice exam (15 questions, weighted to weak topics)" : "+ Generate 5 Questions (teacher-style)"}
        </button>
      )}
      {offline && <div style={{ fontSize: 11, color: "#9A9AA0" }}>Sidecar offline — questions/grades won't be saved.</div>}

      {isExam && assessmentId && !summary && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12, color: "#9A9AA0" }}>
          <b style={{ color: "white", fontVariantNumeric: "tabular-nums" }}>{mm}:{ss}</b>
          <span>Question {current + 1} / {qs.length}</span>
          <span style={{ flex: 1, height: 4, background: "#2A2A2E", borderRadius: 2 }}>
            <span style={{ display: "block", height: 4, width: `${(gradedCount / Math.max(1, qs.length)) * 100}%`, background: "#4f8cff", borderRadius: 2 }} />
          </span>
          <button className="u-btn" onClick={() => setPaused((p) => !p)}>{paused ? "Resume" : "Pause"}</button>
          <button className="u-btn" onClick={finishExam}>Finish &amp; grade all</button>
        </div>
      )}

      {qs.map((q, i) => {
        const examHidden = isExam && !summary && i !== current;
        const g = grades[q.id];
        return (
          <div key={q.id} className="file" style={{ gap: 8, display: examHidden ? "none" : "flex" }}>
            {isExam && <div style={{ fontSize: 11, color: "#9A9AA0" }}>Question {i + 1} of {qs.length} · {q.topic}</div>}
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
            <div style={{ display: "flex", gap: 8 }}>
              <button className="u-btn" onClick={() => grade(q.id)}>Grade</button>
              {isExam && i < qs.length - 1 && !summary && (
                <button className="u-btn" onClick={() => setCurrent(i + 1)}>Next question</button>
              )}
            </div>
            {g && (
              <div style={{ fontSize: 12 }}>
                Score: <b>{g.score}%</b>
                {g.topic && <span style={{ color: "#9A9AA0" }}> · topic: {g.topic}</span>}
                {g.via && <span style={{ color: "#9A9AA0" }}> · {g.via}</span>}
                {" — "}
                {g.reasoning}{" "}
                {!isExam && (
                  <button className="u-btn" onClick={() => grade(q.id)} style={{ marginLeft: 6 }}>
                    Re-grade (dispute)
                  </button>
                )}
              </div>
            )}
          </div>
        );
      })}

      {summary && (
        <div ref={summaryRef} className="file" style={{ gap: 8 }}>
          <div style={{ fontSize: 14, fontWeight: 700 }}>Exam summary</div>
          <div style={{ fontSize: 13 }}>Overall: <b>{summary.overall}%</b> across {gradedCount} graded questions</div>
          <div style={{ fontSize: 12, color: "#9A9AA0" }}>Per topic:</div>
          {Object.entries(summary.perTopic).map(([t, v]) => (
            <div key={t} style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 130, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t}</span>
              <span style={{ flex: 1, height: 6, background: "#2A2A2E", borderRadius: 3 }}>
                <span style={{ display: "block", height: 6, width: `${Math.round(v.total / v.n)}%`, background: v.total / v.n >= 80 ? "#17a34a" : "#e14b4b", borderRadius: 3 }} />
              </span>
              <b>{Math.round(v.total / v.n)}%</b>
            </div>
          ))}
          <div style={{ fontSize: 12, color: "#9A9AA0" }}>Mastery after this exam:</div>
          {summary.mastery.length === 0 && <div style={{ fontSize: 12 }}>No mastery rows yet.</div>}
          {summary.mastery.map((m) => (
            <div key={m.topic} style={{ fontSize: 12, display: "flex", gap: 8 }}>
              <span style={{ width: 130, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.topic}</span>
              <b style={{ color: m.mastery_bool ? "#17a34a" : Math.round((m.score_last || 0) * 100) < 80 ? "#e14b4b" : "white" }}>
                {m.mastery_bool ? "mastered" : Math.round((m.score_last || 0) * 100) < 80 ? "weak" : "in progress"}
              </b>
              <span style={{ color: "#9A9AA0" }}>{Math.round((m.score_last || 0) * 100)}%</span>
            </div>
          ))}
          <button className="u-btn" onClick={reset} style={{ alignSelf: "flex-start" }}>New assessment</button>
        </div>
      )}
    </div>
  );
}
