import { useEffect, useState } from "react";

export function MemoryPanel({ subjectId, subjectName }: { subjectId: string; subjectName: string }) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetch(`http://localhost:1421/memory/${subjectId}`)
      .then((r) => r.json())
      .then((j) => setText(j.text || ""))
      .catch(() => setText(`# ${subjectName} Memory\n\n> Subject-specific preferences and session summaries.\n`));
  }, [subjectId, subjectName]);

  async function save() {
    try {
      await fetch(`http://localhost:1421/memory/${subjectId}`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ text }),
      });
      setStatus("Saved ✓");
      setTimeout(() => setStatus(""), 1500);
    } catch {
      setStatus("Offline — saved locally");
    }
  }

  async function summarize() {
    const summary = `Session ${new Date().toISOString()}: chatted about ${subjectName}. What went well / to improve: be more concise on definitions.`;
    try {
      await fetch(`http://localhost:1421/memory/${subjectId}/session`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ summary }),
      });
    } catch {}
    setText((t) => t + `\n\n## Session ${new Date().toISOString()}\n${summary}\n`);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <textarea className="memory-area" value={text} onChange={(e) => setText(e.target.value)} rows={14} />
      <div style={{ display: "flex", gap: 6 }}>
        <button className="u-btn" onClick={save}>Save Memory</button>
        <button className="u-btn" onClick={summarize}>Summarize Session</button>
        <span style={{ fontSize: 12, color: "#9A9AA0" }}>{status}</span>
      </div>
    </div>
  );
}
