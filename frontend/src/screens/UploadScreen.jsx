import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { startDemo, uploadPDFs } from '../api'

const FEATURES = [
  { icon: '🧠', title: 'Semantic Clustering', desc: 'HDBSCAN groups similar answers across all 100 papers automatically' },
  { icon: '⚡', title: 'One-Action Grading', desc: 'Grade 40 identical answers in a single click — not 40 separate reads' },
  { icon: '🌐', title: 'Hindi + English', desc: 'Gemini reads mixed-language answers and diagrams with full accuracy' },
  { icon: '📊', title: 'Edge Case Isolation', desc: 'Unique answers flagged separately for careful manual review' },
]

export default function UploadScreen() {
  const navigate = useNavigate()
  const fileRef = useRef()
  const [files, setFiles] = useState([])
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState('')

  const onDrop = (e) => {
    e.preventDefault(); setDragging(false)
    const dropped = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.pdf'))
    setFiles(prev => [...prev, ...dropped])
  }

  const onFileChange = (e) => {
    setFiles(prev => [...prev, ...Array.from(e.target.files)])
  }

  const handleDemo = async () => {
    setLoading(true); setLoadingMsg('Loading demo data…')
    try {
      const { data } = await startDemo()
      navigate(`/dashboard/${data.exam_id}`)
    } catch {
      alert('Failed to start demo. Is the backend running?')
    } finally { setLoading(false) }
  }

  const handleUpload = async () => {
    if (!files.length) return
    setLoading(true); setLoadingMsg('Uploading PDFs…')
    try {
      const { data } = await uploadPDFs(files)
      navigate(`/dashboard/${data.exam_id}`)
    } catch {
      alert('Upload failed. Is the backend running?')
    } finally { setLoading(false) }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Nav */}
      <nav style={{ padding: '20px 40px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--accent)', display: 'grid', placeItems: 'center', fontSize: 18 }}>⚡</div>
        <span style={{ fontWeight: 800, fontSize: '1.1rem', letterSpacing: '-0.02em' }}>GradeSync <span style={{ color: 'var(--accent)' }}>AI</span></span>
        <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: '0.8rem' }}>v1.0 · Hackathon Build</span>
      </nav>

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '60px 24px' }}>
        {/* Hero */}
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          style={{ textAlign: 'center', maxWidth: 680, marginBottom: 56 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 16px',
            background: 'var(--accent-dim)', borderRadius: 999, marginBottom: 24,
            border: '1px solid rgba(99,102,241,0.3)', fontSize: '0.82rem', color: 'var(--accent-light)', fontWeight: 600 }}>
            <span>✨</span> AI-Powered Grading Acceleration
          </div>
          <h1 style={{ marginBottom: 16, background: 'linear-gradient(135deg, #e6edf3 0%, #818cf8 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Grade 100 Papers in the Time It Takes to Read 10
          </h1>
          <p style={{ fontSize: '1.1rem', lineHeight: 1.7 }}>
            Upload scanned answer booklets. GradeSync clusters semantically identical answers
            so you grade each <em style={{ color: 'var(--accent-light)' }}>distinct answer type once</em> and apply it to all matching papers simultaneously.
          </p>
        </motion.div>

        <div style={{ width: '100%', maxWidth: 760, display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Demo CTA */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <div className="card" style={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(129,140,248,0.05) 100%)',
              border: '1px solid rgba(99,102,241,0.4)', display: 'flex', alignItems: 'center', gap: 20, padding: '24px 28px' }}>
              <div style={{ flex: 1 }}>
                <h3 style={{ marginBottom: 4 }}>🚀 Try the Live Demo</h3>
                <p style={{ fontSize: '0.9rem' }}>40 students · 4 DSA questions · pre-clustered and ready to grade. No PDF upload needed.</p>
              </div>
              <button className="btn btn-primary btn-lg" onClick={handleDemo} disabled={loading}
                style={{ animation: loading ? 'none' : 'pulse-glow 2s ease-in-out infinite', flexShrink: 0 }}>
                {loading && loadingMsg.includes('demo') ? <><span className="spinner" /> Loading…</> : '⚡ Launch Demo'}
              </button>
            </div>
          </motion.div>

          {/* Divider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, color: 'var(--text-muted)', fontSize: '0.82rem' }}>
            <hr style={{ flex: 1, border: 'none', borderTop: '1px solid var(--border)' }} />
            or upload your own PDFs
            <hr style={{ flex: 1, border: 'none', borderTop: '1px solid var(--border)' }} />
          </div>

          {/* Upload zone */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <div
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              onClick={() => fileRef.current?.click()}
              style={{
                border: `2px dashed ${dragging ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: 'var(--radius-xl)',
                padding: '48px 32px',
                textAlign: 'center',
                cursor: 'pointer',
                background: dragging ? 'var(--accent-dim)' : 'var(--bg-surface)',
                transition: 'all 0.2s ease',
              }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>📄</div>
              <h3 style={{ marginBottom: 8 }}>Drag & drop PDF answer booklets here</h3>
              <p style={{ fontSize: '0.9rem', marginBottom: 20 }}>One PDF per student · Supports scanned booklets · Hindi + English</p>
              <button className="btn btn-secondary" onClick={e => { e.stopPropagation(); fileRef.current?.click() }}>
                Browse Files
              </button>
              <input ref={fileRef} type="file" accept=".pdf" multiple hidden onChange={onFileChange} />
            </div>

            {/* File list */}
            {files.length > 0 && (
              <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{files.length} file{files.length !== 1 ? 's' : ''} selected</span>
                  <button onClick={() => setFiles([])} className="btn btn-ghost btn-sm">Clear</button>
                </div>
                <div style={{ maxHeight: 180, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {files.map((f, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 14px',
                      background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
                      <span>📄</span>
                      <span style={{ flex: 1, fontSize: '0.85rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{(f.size / 1024).toFixed(0)} KB</span>
                    </div>
                  ))}
                </div>
                <button className="btn btn-primary w-full" onClick={handleUpload} disabled={loading} style={{ marginTop: 8 }}>
                  {loading ? <><span className="spinner" /> {loadingMsg}</> : `🚀 Process ${files.length} Paper${files.length !== 1 ? 's' : ''}`}
                </button>
              </div>
            )}
          </motion.div>
        </div>

        {/* Features */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
          style={{ marginTop: 80, width: '100%', maxWidth: 760, display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
          {FEATURES.map((f, i) => (
            <div key={i} className="card" style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
              <div style={{ fontSize: 28, lineHeight: 1 }}>{f.icon}</div>
              <div>
                <h4 style={{ marginBottom: 4 }}>{f.title}</h4>
                <p style={{ fontSize: '0.85rem' }}>{f.desc}</p>
              </div>
            </div>
          ))}
        </motion.div>
      </main>
    </div>
  )
}
