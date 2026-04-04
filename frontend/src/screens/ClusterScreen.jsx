import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { getExamClusters, getSummary } from '../api'

function formatGradeBand(band) {
  if (!band) return 'Mixed'
  if (typeof band !== 'string') return 'Mixed'
  if (band === 'formula_half_credit') return 'Formula correct, arithmetic wrong'
  if (band === 'excellent') return 'Excellent'
  if (band === 'good') return 'Good'
  if (band === 'average') return 'Average'
  if (band === 'poor') return 'Needs Improvement'
  return band
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function ClusterCard({ cluster }) {
  const [expanded, setExpanded] = useState(false)

  const isOutlier = cluster.is_outlier
  const baseColor = isOutlier ? 'var(--incorrect)' : 'var(--accent-light)'
  const bgDim = isOutlier ? 'rgba(239,68,68,0.08)' : 'rgba(99,102,241,0.08)'
  const borderDim = isOutlier ? 'rgba(239,68,68,0.2)' : 'rgba(99,102,241,0.2)'

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="card"
      style={{
        padding: 24,
        marginBottom: 20,
        border: `1px solid ${borderDim}`,
        background: 'var(--bg-surface)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 12 }}>
        <div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <h3 style={{ margin: 0, color: baseColor }}>{cluster.cluster_name}</h3>
            {isOutlier && <span className="badge" style={{ background: 'var(--incorrect)', color: '#fff' }}>Uncommon Answers</span>}
          </div>
          <div style={{ fontSize: '0.86rem', color: 'var(--text-muted)', marginTop: 4 }}>
            {cluster.student_count} student{cluster.student_count === 1 ? '' : 's'} | {formatGradeBand(cluster.grade_band)} | Avg score {cluster.avg_score}
          </div>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={() => setExpanded(!expanded)}>
          {expanded ? 'Hide Students' : 'View Students'}
        </button>
      </div>

      <div
        style={{
          padding: '16px',
          background: bgDim,
          borderRadius: 'var(--radius-md)',
          border: `1px solid ${borderDim}`,
          marginBottom: expanded ? 16 : 0,
        }}
      >
        <div style={{ fontSize: '0.74rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: baseColor, marginBottom: 6 }}>
          Cluster Insight
        </div>
        <p style={{ margin: 0, fontSize: '0.94rem', lineHeight: 1.5, color: 'var(--text-primary)' }}>
          {cluster.insight}
        </p>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: 12, marginTop: 16 }}>
              {cluster.students.map((student, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: 16,
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <div>
                      <strong style={{ fontSize: '0.9rem' }}>{student.name}</strong>
                      <span style={{ marginLeft: 8, fontSize: '0.8rem', color: 'var(--text-muted)' }} className="mono">{student.roll_number}</span>
                    </div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-light)' }}>
                      Score: {student.score}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 8 }}>
                    {formatGradeBand(student.grade_band)} | Rubric {((student.concept_coverage || 0) * 100).toFixed(0)}%
                  </div>
                  <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', padding: '10px 12px', background: 'var(--bg-surface)', borderRadius: 6 }}>
                    "{student.answer_text}"
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function ClusterScreen() {
  const { examId } = useParams()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState(null)
  const [clustersData, setClustersData] = useState({})
  const [selectedQ, setSelectedQ] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let intervalId

    async function loadData() {
      try {
        const sumResp = await getSummary(examId)
        setSummary(sumResp.data)

        const cluResp = await getExamClusters(examId)
        setClustersData(cluResp.data.clusters || {})

        if (sumResp.data.questions?.length > 0 && !selectedQ) {
          setSelectedQ(sumResp.data.questions[0].q_number)
        }

        setLoading(false)
        clearInterval(intervalId)
      } catch (err) {
        console.error(err)
        setError('Failed to load clusters. Ensure the exam grading run has completed successfully.')
        setLoading(false)
        clearInterval(intervalId)
      }
    }

    loadData()
    intervalId = setInterval(loadData, 2000)

    return () => clearInterval(intervalId)
  }, [examId, selectedQ])

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 32 }}>
        <div style={{ textAlign: 'center' }}>
          <div className="spinner" style={{ width: 40, height: 40, marginBottom: 16 }}></div>
          <h2>Loading Cluster Insights...</h2>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 32 }}>
        <div className="card" style={{ maxWidth: 500, textAlign: 'center', padding: 32 }}>
          <h2>Unable to Load</h2>
          <p>{error}</p>
          <button className="btn btn-secondary" onClick={() => navigate(`/dashboard/${examId}`)} style={{ marginTop: 20 }}>
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  const currentClusters = clustersData[selectedQ] || []

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 16, background: 'var(--bg-surface)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }} onClick={() => navigate('/')}>
          <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--accent)', display: 'grid', placeItems: 'center', fontSize: 14 }}>AI</div>
          <span style={{ fontWeight: 800 }}>GradeSync <span style={{ color: 'var(--accent)' }}>AI</span></span>
        </div>

        <div>
          <div style={{ fontWeight: 700 }}>Semantic Clustering Insights</div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            {summary?.title}
          </div>
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 12 }}>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/dashboard/${examId}`)}>
            Back to Dashboard
          </button>
        </div>
      </header>

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '240px 1fr', minHeight: 0 }}>
        <aside style={{ borderRight: '1px solid var(--border)', padding: '18px 12px', background: 'var(--bg-surface)', overflowY: 'auto' }}>
          <div style={{ fontSize: '0.72rem', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, padding: '0 8px 10px' }}>
            Questions
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {summary?.questions?.map((question) => {
              const active = selectedQ === question.q_number
              const clusterCount = clustersData[question.q_number]?.length || 0
              return (
                <button
                  key={question.q_number}
                  className="btn"
                  onClick={() => setSelectedQ(question.q_number)}
                  style={{
                    padding: '12px',
                    justifyContent: 'flex-start',
                    background: active ? 'var(--accent-dim)' : 'transparent',
                    color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                    border: `1px solid ${active ? 'rgba(99,102,241,0.35)' : 'transparent'}`,
                  }}
                >
                  <div style={{ textAlign: 'left', width: '100%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                      <span style={{ fontWeight: 700 }}>{question.q_number}</span>
                      <span style={{ fontSize: '0.74rem', background: 'var(--bg-card)', padding: '2px 6px', borderRadius: 4 }}>
                        {clusterCount} groups
                      </span>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </aside>

        <main style={{ padding: '32px 48px', overflowY: 'auto', background: 'var(--bg-background)' }}>
          <div style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: '2rem', marginBottom: 8 }}>Analysis for {selectedQ}</h2>
            <p style={{ color: 'var(--text-secondary)' }}>
              Answers are grouped by semantic similarity after grading so correct, partial, and incorrect reasoning patterns stay separated.
            </p>
          </div>

          {currentClusters.length === 0 ? (
            <div className="card" style={{ padding: 40, textAlign: 'center' }}>
              <div style={{ fontSize: 40, marginBottom: 16 }}>No data</div>
              <h3>No clusters available</h3>
              <p style={{ color: 'var(--text-muted)' }}>Clustering is still processing or there were not enough student answers for this question.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {currentClusters.map((cluster) => (
                <ClusterCard key={cluster.cluster_id} cluster={cluster} />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
