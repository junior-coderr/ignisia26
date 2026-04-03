import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { getSummary, getClusters, applyGrade, getStatus } from '../api'
import ClusterCard from '../components/ClusterCard'
import ClusterDetailModal from '../components/ClusterDetailModal'

const TYPE_ICON = { correct: '✅', partial: '⚠️', incorrect: '❌', edge_case: '🔮' }

export default function DashboardScreen() {
  const { examId } = useParams()
  const navigate = useNavigate()

  const [summary, setSummary] = useState(null)
  const [selectedQ, setSelectedQ] = useState(null)
  const [qData, setQData] = useState(null)
  const [loadingQ, setLoadingQ] = useState(false)
  const [modalCluster, setModalCluster] = useState(null)
  const [status, setStatus] = useState('loading')
  const [progress, setProgress] = useState(0)
  const [gradingStats, setGradingStats] = useState({ overall: 0, graded: 0, total: 0 })

  // Poll status until ready
  useEffect(() => {
    let interval
    const poll = async () => {
      try {
        const { data } = await getStatus(examId)
        setProgress(data.progress || 0)
        if (data.status === 'ready') {
          clearInterval(interval)
          setStatus('ready')
          loadSummary()
        } else if (data.status === 'error') {
          clearInterval(interval)
          setStatus('error')
        } else {
          setStatus(data.status)
        }
      } catch { setStatus('error'); clearInterval(interval) }
    }
    poll()
    interval = setInterval(poll, 2000)
    return () => clearInterval(interval)
  }, [examId])

  const loadSummary = useCallback(async () => {
    try {
      const { data } = await getSummary(examId)
      setSummary(data)
      setGradingStats({ overall: data.overall_progress, graded: data.graded_clusters, total: data.total_clusters })
      if (!selectedQ && data.questions?.length) {
        selectQuestion(data.questions[0].q_number)
      }
    } catch (e) { console.error(e) }
  }, [examId, selectedQ])

  const selectQuestion = async (qNum) => {
    setSelectedQ(qNum); setLoadingQ(true); setQData(null)
    try {
      const { data } = await getClusters(examId, qNum)
      setQData(data)
    } catch (e) { console.error(e) }
    finally { setLoadingQ(false) }
  }

  const handleGrade = async (clusterId, score, feedback) => {
    await applyGrade(examId, selectedQ, clusterId, score, feedback)
    // Refresh question data
    const { data } = await getClusters(examId, selectedQ)
    setQData(data)
    setModalCluster(null)
    loadSummary()
  }

  // ── Processing states ──
  if (status !== 'ready') {
    const msgs = {
      loading: 'Connecting…',
      queued: 'Queued — waiting to start…',
      processing: 'Gemini is reading answer booklets…',
      clustering: 'Clustering answers with HDBSCAN…',
      error: 'Something went wrong.',
    }
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 24, padding: 40 }}>
        <div style={{ fontSize: 64 }}>{status === 'error' ? '⚠️' : '⚙️'}</div>
        <h2>{msgs[status] || status}</h2>
        <div style={{ width: 360 }}>
          <div className="progress-bar"><div className="progress-fill" style={{ width: `${(progress * 100).toFixed(0)}%` }} /></div>
          <p style={{ textAlign: 'center', marginTop: 8, fontSize: '0.85rem' }}>{(progress * 100).toFixed(0)}%</p>
        </div>
        {status !== 'error' && <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>This may take 1–2 minutes for large batches</p>}
        {status === 'error' && <button className="btn btn-secondary" onClick={() => navigate('/')}>← Back to Upload</button>}
      </div>
    )
  }

  const allClusters = qData ? [...(qData.clusters || []), ...(qData.edge_cases || [])] : []
  const gradedInQ = allClusters.filter(c => c.graded).length

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* ── Top bar ── */}
      <header style={{ padding: '0 24px', height: 60, borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0, background: 'var(--bg-surface)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }} onClick={() => navigate('/')}>
          <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--accent)', display: 'grid', placeItems: 'center', fontSize: 14 }}>⚡</div>
          <span style={{ fontWeight: 800, fontSize: '0.95rem' }}>GradeSync <span style={{ color: 'var(--accent)' }}>AI</span></span>
        </div>

        {summary && (
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginLeft: 8 }}>
            {summary.title} · {summary.total_students} students
          </span>
        )}

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 20 }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
              {gradingStats.graded}/{gradingStats.total} clusters graded
            </div>
            <div style={{ width: 160 }}>
              <div className="progress-bar" style={{ height: 5 }}>
                <div className="progress-fill" style={{ width: `${(gradingStats.overall * 100).toFixed(0)}%` }} />
              </div>
            </div>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/export/${examId}`)}>
            📤 Export Grades
          </button>
        </div>
      </header>

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* ── Left Sidebar — Question List ── */}
        <aside style={{ width: 240, background: 'var(--bg-surface)', borderRight: '1px solid var(--border)',
          overflowY: 'auto', flexShrink: 0, padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <p style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--text-muted)', padding: '0 8px 8px' }}>Questions</p>
          {summary?.questions?.map(q => {
            const pct = q.total > 0 ? q.graded / q.total : 0
            const isActive = selectedQ === q.q_number
            return (
              <button key={q.q_number} onClick={() => selectQuestion(q.q_number)}
                style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '12px', textAlign: 'left',
                  background: isActive ? 'var(--accent-dim)' : 'transparent',
                  border: `1px solid ${isActive ? 'rgba(99,102,241,0.4)' : 'transparent'}`,
                  borderRadius: 'var(--radius-md)', cursor: 'pointer', transition: 'all 0.15s', width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 700, color: isActive ? 'var(--accent-light)' : 'var(--text-primary)', fontSize: '0.9rem' }}>
                    {q.q_number}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: q.graded === q.total && q.total > 0 ? 'var(--correct)' : 'var(--text-muted)', fontWeight: 600 }}>
                    {q.graded}/{q.total}
                  </span>
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: '-webkit-box', WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{q.q_text}</p>
                <div className="progress-bar" style={{ height: 3 }}>
                  <div className="progress-fill" style={{ width: `${(pct * 100).toFixed(0)}%` }} />
                </div>
              </button>
            )
          })}
        </aside>

        {/* ── Main content ── */}
        <main style={{ flex: 1, overflowY: 'auto', padding: 24, background: 'var(--bg-base)' }}>
          {loadingQ ? (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
              <span className="spinner" style={{ width: 32, height: 32 }} />
            </div>
          ) : qData ? (
            <div>
              {/* Question header */}
              <div style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                  <h2>{qData.q_number}</h2>
                  <span style={{ padding: '4px 12px', background: 'var(--bg-card)', borderRadius: 999,
                    fontSize: '0.8rem', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
                    Max: {qData.max_marks} marks
                  </span>
                  <span style={{ marginLeft: 'auto', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    {gradedInQ}/{allClusters.length} clusters graded
                  </span>
                </div>
                <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)' }}>{qData.q_text}</p>
                {qData.rubric_keywords?.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', alignSelf: 'center' }}>Rubric keywords:</span>
                    {qData.rubric_keywords.map(kw => (
                      <span key={kw} className="badge badge-neutral">{kw}</span>
                    ))}
                  </div>
                )}
              </div>

              {/* Cluster cards */}
              {qData.clusters?.length > 0 && (
                <>
                  <h3 style={{ marginBottom: 12, fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>
                    Clusters ({qData.clusters.length})
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16, marginBottom: 32 }}>
                    <AnimatePresence>
                      {qData.clusters.map((c, i) => (
                        <motion.div key={c.cluster_id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                          <ClusterCard cluster={c} maxMarks={qData.max_marks} onOpen={() => setModalCluster(c)} />
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                </>
              )}

              {/* Edge cases */}
              {qData.edge_cases?.length > 0 && (
                <>
                  <h3 style={{ marginBottom: 12, fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--edge)' }}>
                    🔮 Edge Cases — Manual Review ({qData.edge_cases.length})
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
                    <AnimatePresence>
                      {qData.edge_cases.map((c, i) => (
                        <motion.div key={c.cluster_id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                          <ClusterCard cluster={c} maxMarks={qData.max_marks} onOpen={() => setModalCluster(c)} />
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--text-muted)' }}>
              Select a question from the sidebar
            </div>
          )}
        </main>
      </div>

      {/* Cluster detail modal */}
      <AnimatePresence>
        {modalCluster && (
          <ClusterDetailModal
            cluster={modalCluster}
            qNumber={selectedQ}
            maxMarks={qData?.max_marks || 5}
            rubricKeywords={qData?.rubric_keywords || []}
            onGrade={handleGrade}
            onClose={() => setModalCluster(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
