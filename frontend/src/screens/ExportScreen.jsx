import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { exportCSVUrl, getResults, getSummary } from '../api'

export default function ExportScreen() {
  const { examId } = useParams()
  const navigate = useNavigate()
  const [summary, setSummary] = useState(null)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getSummary(examId), getResults(examId)])
      .then(([summaryResp, resultsResp]) => {
        setSummary(summaryResp.data)
        setResults(resultsResp.data)
      })
      .catch((error) => {
        console.error(error)
      })
      .finally(() => setLoading(false))
  }, [examId])

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <span className="spinner" style={{ width: 34, height: 34 }} />
      </div>
    )
  }

  const questions = results?.questions || []
  const students = results?.students || []

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      <nav style={{ padding: '16px 32px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 16, background: 'var(--bg-surface)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }} onClick={() => navigate(`/dashboard/${examId}`)}>
          <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--accent)', display: 'grid', placeItems: 'center', fontSize: 14 }}>✓</div>
          <span style={{ fontWeight: 800 }}>GradeSync <span style={{ color: 'var(--accent)' }}>AI</span></span>
        </div>
        <span style={{ color: 'var(--text-muted)' }}>Results Export</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 12 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate(`/dashboard/${examId}`)}>Back to Dashboard</button>
          <a href={exportCSVUrl(examId)} download>
            <button className="btn btn-primary btn-sm">Download CSV</button>
          </a>
        </div>
      </nav>

      <main style={{ maxWidth: 1320, margin: '0 auto', padding: '36px 28px 60px' }}>
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <h1 style={{ marginBottom: 8 }}>Auto-Graded Results</h1>
          <p style={{ marginBottom: 26 }}>{summary?.title} · {summary?.exam_code || 'No exam code extracted'}</p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 16, marginBottom: 28 }}>
            {[
              { label: 'Total Students', value: summary?.total_students || 0, icon: '👥' },
              { label: 'Questions', value: summary?.question_count || 0, icon: '📚' },
              { label: 'Class Average', value: `${summary?.class_average || 0}/${summary?.max_total || 0}`, icon: '📊' },
              { label: 'Max Total', value: summary?.max_total || 0, icon: '🏁' },
            ].map((item) => (
              <div key={item.label} className="card" style={{ textAlign: 'center', padding: 20 }}>
                <div style={{ fontSize: 30, marginBottom: 8 }}>{item.icon}</div>
                <div style={{ fontSize: '1.7rem', fontWeight: 800, color: 'var(--accent-light)' }}>{item.value}</div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{item.label}</div>
              </div>
            ))}
          </div>

          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3>Student Scores</h3>
                <p style={{ fontSize: '0.84rem' }}>Each question score is based on cosine similarity against the teacher reference answer for the same question ID.</p>
              </div>
              <a href={exportCSVUrl(examId)} download>
                <button className="btn btn-primary btn-sm">Download CSV</button>
              </a>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 1080 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-surface)' }}>
                    <th style={thStyle}>Roll Number</th>
                    <th style={thStyle}>Name</th>
                    {questions.map((question) => (
                      <th key={question.q_number} style={thStyle}>{question.q_number} / {question.max_marks}</th>
                    ))}
                    <th style={{ ...thStyle, color: 'var(--accent-light)' }}>Total / {results?.max_total || 0}</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((student, rowIndex) => (
                    <tr key={student.roll_number} style={{ borderTop: '1px solid var(--border)', background: rowIndex % 2 ? 'rgba(255,255,255,0.01)' : 'transparent' }}>
                      <td style={tdStyle}><span className="mono">{student.roll_number}</span></td>
                      <td style={tdStyle}>{student.name}</td>
                      {questions.map((question) => {
                        const score = student.scores?.[question.q_number]
                        return (
                          <td key={question.q_number} style={tdStyle}>
                            <div style={{ fontWeight: 700 }}>{score?.score ?? 0}/{question.max_marks}</div>
                            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                              {score?.attempted ? `${((score.similarity || 0) * 100).toFixed(0)}% sim` : 'Not attempted'}
                            </div>
                          </td>
                        )
                      })}
                      <td style={{ ...tdStyle, fontWeight: 800, color: 'var(--accent-light)' }}>{student.total}</td>
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
  padding: '12px 16px',
  textAlign: 'left',
  fontWeight: 700,
  fontSize: '0.76rem',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  color: 'var(--text-muted)',
}

const tdStyle = {
  padding: '12px 16px',
  verticalAlign: 'top',
}
