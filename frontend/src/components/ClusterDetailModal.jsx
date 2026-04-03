import { useState } from 'react'
import { motion } from 'framer-motion'

const TYPE_COLORS = {
  correct:   { color: 'var(--correct)',   bg: 'var(--correct-bg)' },
  partial:   { color: 'var(--partial)',   bg: 'var(--partial-bg)' },
  incorrect: { color: 'var(--incorrect)', bg: 'var(--incorrect-bg)' },
  edge_case: { color: 'var(--edge)',      bg: 'var(--edge-bg)' },
}
const TYPE_ICON = { correct: '✅', partial: '⚠️', incorrect: '❌', edge_case: '🔮' }

function highlightKeywords(text, keywords) {
  if (!keywords?.length || !text) return <>{text}</>
  const escaped = keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const regex = new RegExp(`(${escaped.join('|')})`, 'gi')
  const parts = text.split(regex)
  return (
    <>
      {parts.map((p, i) =>
        keywords.some(k => k.toLowerCase() === p.toLowerCase())
          ? <mark key={i} className="kw-highlight">{p}</mark>
          : p
      )}
    </>
  )
}

export default function ClusterDetailModal({ cluster, qNumber, maxMarks, rubricKeywords, onGrade, onClose }) {
  const [score, setScore] = useState(cluster.score ?? (cluster.suggested_score ?? ''))
  const [feedback, setFeedback] = useState(cluster.feedback ?? '')
  const [saving, setSaving] = useState(false)
  const tc = TYPE_COLORS[cluster.type] || TYPE_COLORS.partial

  const handleGrade = async () => {
    if (score === '' || score === null) return
    setSaving(true)
    try { await onGrade(cluster.cluster_id, parseFloat(score), feedback) }
    finally { setSaving(false) }
  }

  return (
    <motion.div className="modal-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <motion.div className="modal-box" initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95 }}>
        {/* Header */}
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', gap: 14, position: 'sticky', top: 0,
          background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl) var(--radius-xl) 0 0', zIndex: 5 }}>
          <div style={{ width: 40, height: 40, borderRadius: 12, background: tc.bg,
            display: 'grid', placeItems: 'center', fontSize: 20 }}>
            {TYPE_ICON[cluster.type]}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: tc.color,
                textTransform: 'uppercase', letterSpacing: '0.06em' }}>{cluster.type?.replace('_', ' ')}</span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>·</span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{cluster.student_count} students</span>
            </div>
            <h3 style={{ fontSize: '1rem' }}>{cluster.label}</h3>
          </div>
          <button onClick={onClose} className="btn btn-ghost btn-sm" style={{ fontSize: '1.2rem', padding: '6px 10px' }}>×</button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 0 }}>
          {/* Left: all student answers */}
          <div style={{ padding: 24, borderRight: '1px solid var(--border)', maxHeight: '70vh', overflowY: 'auto' }}>
            <p style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
              color: 'var(--text-muted)', marginBottom: 16 }}>
              All Answers in This Cluster
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {cluster.students?.map((stu, i) => (
                <div key={stu.roll_number + i} style={{ background: 'var(--bg-card)', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)', padding: 14 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <div style={{ width: 28, height: 28, borderRadius: '50%', background: tc.bg,
                      display: 'grid', placeItems: 'center', fontSize: '0.7rem', fontWeight: 700, color: tc.color }}>
                      {(stu.name || 'S').charAt(0).toUpperCase()}
                    </div>
                    <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{stu.name}</span>
                    <span className="mono" style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: 'auto' }}>
                      {stu.roll_number}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                    {highlightKeywords(stu.answer?.text || stu.combined_text?.replace('[Text]: ', ''), rubricKeywords)}
                  </p>
                  {stu.answer?.diagram_present && stu.answer?.diagram_description && (
                    <div style={{ marginTop: 8, padding: '8px 12px', background: 'rgba(99,102,241,0.08)',
                      borderRadius: 6, border: '1px solid rgba(99,102,241,0.2)', fontSize: '0.8rem', color: 'var(--accent-light)' }}>
                      📐 <strong>Diagram:</strong> {stu.answer.diagram_description}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Right: grading panel */}
          <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20, maxHeight: '70vh', overflowY: 'auto' }}>
            <div>
              <p style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
                color: 'var(--text-muted)', marginBottom: 16 }}>Grading Panel</p>

              {/* Keyword matches */}
              {cluster.matched_keywords?.length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 8 }}>Matched rubric keywords:</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {cluster.matched_keywords.map(kw => (
                      <span key={kw} className="badge" style={{ background: 'rgba(99,102,241,0.12)', color: 'var(--accent-light)' }}>
                        ✓ {kw}
                      </span>
                    ))}
                  </div>
                  <div style={{ marginTop: 10 }}>
                    <div className="progress-bar" style={{ height: 5 }}>
                      <div className="progress-fill" style={{ width: `${(cluster.keyword_match_pct * 100).toFixed(0)}%` }} />
                    </div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                      {(cluster.keyword_match_pct * 100).toFixed(0)}% keyword coverage
                    </p>
                  </div>
                </div>
              )}

              {/* Score input */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: 8 }}>
                  Score (out of {maxMarks})
                  {cluster.suggested_score != null && (
                    <button onClick={() => setScore(cluster.suggested_score)}
                      style={{ marginLeft: 10, fontSize: '0.72rem', color: 'var(--accent-light)',
                        background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>
                      Use AI suggestion ({cluster.suggested_score})
                    </button>
                  )}
                </label>
                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  {Array.from({ length: maxMarks + 1 }, (_, i) => i).map(v => (
                    <button key={v} onClick={() => setScore(v)}
                      style={{ flex: 1, padding: '10px 4px', borderRadius: 8, border: '1px solid',
                        cursor: 'pointer', transition: 'all 0.15s', fontWeight: 700, fontSize: '0.9rem',
                        borderColor: score === v ? 'var(--accent)' : 'var(--border)',
                        background: score === v ? 'var(--accent)' : 'var(--bg-surface)',
                        color: score === v ? '#fff' : 'var(--text-secondary)' }}>
                      {v}
                    </button>
                  ))}
                </div>
              </div>

              {/* Feedback */}
              <div style={{ marginBottom: 24 }}>
                <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: 8 }}>Feedback (optional)</label>
                <textarea className="input" value={feedback} onChange={e => setFeedback(e.target.value)}
                  placeholder="e.g. Good explanation but missing the time complexity analysis." rows={4} />
              </div>

              {/* Apply button — the big moment */}
              <button className="btn btn-primary w-full"
                disabled={score === '' || saving}
                onClick={handleGrade}
                style={{ padding: '16px', fontSize: '1rem',
                  boxShadow: score !== '' ? '0 0 30px var(--accent-glow)' : 'none' }}>
                {saving
                  ? <><span className="spinner" /> Applying…</>
                  : <>⚡ Apply to All {cluster.student_count} Papers</>}
              </button>
              <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 10 }}>
                This grades {cluster.student_count} student{cluster.student_count !== 1 ? 's' : ''} simultaneously
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
