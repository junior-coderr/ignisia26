import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { exportGradesJSON, exportCSVUrl, getSummary } from '../api'

export default function ExportScreen() {
  const { examId } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([exportGradesJSON(examId), getSummary(examId)])
      .then(([g, s]) => { setData(g.data); setSummary(s.data) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [examId])

  if (loading) return (
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <span className="spinner" style={{ width: 40, height: 40 }} />
    </div>
  )

  const questions = summary?.questions || []
  const students = data?.students || []
  const maxTotal = questions.reduce((s, q) => s + (q.max_marks || 5), 0)

  const avgScore = students.length
    ? (students.reduce((s, st) => s + st.total, 0) / students.length).toFixed(1)
    : 0

  const gradedCount = students.filter(s => s.total > 0).length

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      {/* Nav */}
      <nav style={{ padding: '16px 32px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 16, background: 'var(--bg-surface)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }} onClick={() => navigate('/')}>
          <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--accent)', display: 'grid', placeItems: 'center', fontSize: 14 }}>⚡</div>
          <span style={{ fontWeight: 800 }}>GradeSync <span style={{ color: 'var(--accent)' }}>AI</span></span>
        </div>
        <span style={{ color: 'var(--border)' }}>›</span>
        <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Export Grades</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 12 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate(`/dashboard/${examId}`)}>← Back to Dashboard</button>
          <a href={exportCSVUrl(examId)} download>
            <button className="btn btn-primary btn-sm">⬇ Download CSV</button>
          </a>
        </div>
      </nav>

      <main style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 32px' }}>
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h1 style={{ marginBottom: 8 }}>Grade Report</h1>
          <p style={{ marginBottom: 32 }}>{summary?.title} · {summary?.exam_code}</p>

          {/* Summary Stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 40 }}>
            {[
              { label: 'Total Students', value: students.length, icon: '👥' },
              { label: 'Graded Students', value: gradedCount, icon: '✅' },
              { label: 'Class Average', value: `${avgScore}/${maxTotal}`, icon: '📊' },
              { label: 'Grading Progress', value: `${(summary?.overall_progress * 100 || 0).toFixed(0)}%`, icon: '⚡' },
            ].map((s, i) => (
              <div key={i} className="card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>{s.icon}</div>
                <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--accent-light)' }}>{s.value}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 4 }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Grades Table */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h3>Student Grades</h3>
              <a href={exportCSVUrl(examId)} download>
                <button className="btn btn-primary btn-sm">⬇ Download CSV</button>
              </a>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                <thead>
                  <tr style={{ background: 'var(--bg-surface)' }}>
                    <th style={thStyle}>Roll Number</th>
                    <th style={thStyle}>Name</th>
                    {questions.map(q => (
                      <th key={q.q_number} style={thStyle}>{q.q_number} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>/{q.max_marks}</span></th>
                    ))}
                    <th style={{ ...thStyle, color: 'var(--accent-light)' }}>Total /{maxTotal}</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((stu, i) => (
                    <tr key={stu.roll_number} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)' }}>
                      <td style={tdStyle}><span className="mono" style={{ color: 'var(--text-muted)' }}>{stu.roll_number}</span></td>
                      <td style={tdStyle}>{stu.name}</td>
                      {questions.map(q => {
                        const sc = stu.scores?.[q.q_number]?.score
                        return (
                          <td key={q.q_number} style={{ ...tdStyle, textAlign: 'center' }}>
                            {sc != null
                              ? <span style={{ color: sc >= q.max_marks * 0.8 ? 'var(--correct)' : sc >= q.max_marks * 0.5 ? 'var(--partial)' : 'var(--incorrect)', fontWeight: 600 }}>{sc}</span>
                              : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                          </td>
                        )
                      })}
                      <td style={{ ...tdStyle, textAlign: 'center', fontWeight: 700, color: 'var(--accent-light)' }}>{stu.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      </main>
    </div>
  )
}

const thStyle = {
  padding: '12px 16px', textAlign: 'left', fontWeight: 600,
  fontSize: '0.78rem', color: 'var(--text-secondary)',
  textTransform: 'uppercase', letterSpacing: '0.05em',
  borderBottom: '1px solid var(--border)',
}
const tdStyle = { padding: '12px 16px' }
