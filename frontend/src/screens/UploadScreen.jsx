import { useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { uploadReferencePDF } from '../api'

const FLOW_STEPS = [
  {
    title: 'Upload Reference Sheet',
    desc: 'Teacher uploads one official answer key containing the correct answers and question marks.',
  },
  {
    title: 'Upload Student PDFs',
    desc: 'Student cover pages and answers are extracted with Gemini into structured question-level data.',
  },
  {
    title: 'Auto Grade by Similarity',
    desc: 'Each student answer is embedded and compared only against the matching reference question ID.',
  },
]

export default function UploadScreen() {
  const navigate = useNavigate()
  const fileRef = useRef(null)
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    try {
      const { data } = await uploadReferencePDF(file)
      navigate(`/dashboard/${data.exam_id}`)
    } catch (error) {
      console.error(error)
      alert('Reference upload failed. Make sure the backend is running and the PDF is valid.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <nav style={{ padding: '20px 40px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--accent)', display: 'grid', placeItems: 'center', fontSize: 18 }}>✓</div>
        <span style={{ fontWeight: 800, fontSize: '1.1rem', letterSpacing: '-0.02em' }}>GradeSync <span style={{ color: 'var(--accent)' }}>AI</span></span>
        <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: '0.8rem' }}>Reference-first auto grading</span>
      </nav>

      <main style={{ flex: 1, padding: '56px 24px 72px', display: 'grid', placeItems: 'center' }}>
        <div style={{ width: '100%', maxWidth: 1120, display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 28 }}>
          <motion.section
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="card"
            style={{
              padding: 36,
              background: 'radial-gradient(circle at top left, rgba(99,102,241,0.18), transparent 45%), var(--bg-card)',
            }}
          >
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 14px', borderRadius: 999, background: 'var(--accent-dim)', color: 'var(--accent-light)', fontSize: '0.8rem', fontWeight: 700, marginBottom: 20 }}>
              Step 1 of 2
            </div>
            <h1 style={{ maxWidth: 620, marginBottom: 14 }}>
              Upload the teacher&apos;s correct answer sheet first
            </h1>
            <p style={{ fontSize: '1.02rem', maxWidth: 640, marginBottom: 30 }}>
              The system extracts question IDs, question text, ideal answers, and full marks from one reference PDF.
              Those reference answers are embedded once and reused for automatic grading.
            </p>

            <div
              onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault()
                setDragging(false)
                const dropped = Array.from(event.dataTransfer.files).find((entry) => entry.name.toLowerCase().endsWith('.pdf'))
                if (dropped) setFile(dropped)
              }}
              onClick={() => fileRef.current?.click()}
              style={{
                border: `2px dashed ${dragging ? 'var(--accent)' : 'var(--border-light)'}`,
                borderRadius: 'var(--radius-xl)',
                padding: '44px 28px',
                cursor: 'pointer',
                background: dragging ? 'var(--accent-dim)' : 'var(--bg-surface)',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ fontSize: 44, marginBottom: 12 }}>📘</div>
              <h3 style={{ marginBottom: 8 }}>Drop the reference answer PDF here</h3>
              <p style={{ fontSize: '0.92rem', marginBottom: 18 }}>
                One teacher reference sheet with question numbers, correct answers, and question marks.
              </p>
              <button className="btn btn-secondary" onClick={(event) => { event.stopPropagation(); fileRef.current?.click() }}>
                Browse Reference PDF
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf"
                hidden
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
            </div>

            {file && (
              <div className="card" style={{ marginTop: 18, padding: 16, background: 'var(--bg-surface)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 20 }}>📄</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{(file.size / 1024).toFixed(0)} KB</div>
                  </div>
                  <button className="btn btn-ghost btn-sm" onClick={() => setFile(null)}>Clear</button>
                </div>
                <button className="btn btn-primary w-full" disabled={loading} onClick={handleUpload} style={{ marginTop: 14 }}>
                  {loading ? <><span className="spinner" /> Processing reference…</> : 'Create Exam From Reference'}
                </button>
              </div>
            )}
          </motion.section>

          <motion.aside
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.08 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 18 }}
          >
            <div className="card" style={{ padding: 28 }}>
              <h3 style={{ marginBottom: 8 }}>Working Flow</h3>
              <p style={{ fontSize: '0.92rem', marginBottom: 18 }}>
                The application is now centered on reference-answer matching, not clustering.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {FLOW_STEPS.map((step, index) => (
                  <div key={step.title} style={{ display: 'grid', gridTemplateColumns: '28px 1fr', gap: 12, alignItems: 'start' }}>
                    <div style={{ width: 28, height: 28, borderRadius: 999, background: 'var(--accent-dim)', color: 'var(--accent-light)', display: 'grid', placeItems: 'center', fontWeight: 700, fontSize: '0.82rem' }}>
                      {index + 1}
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, marginBottom: 3 }}>{step.title}</div>
                      <p style={{ fontSize: '0.86rem' }}>{step.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card" style={{ padding: 28, background: 'linear-gradient(180deg, rgba(99,102,241,0.08), transparent 70%), var(--bg-card)' }}>
              <h3 style={{ marginBottom: 10 }}>What gets extracted</h3>
              <div style={{ display: 'grid', gap: 10, fontSize: '0.9rem' }}>
                <div>Teacher sheet: `Q ID`, question text, full marks, correct answer, diagram description.</div>
                <div>Student sheets: page 1 metadata, then per-question student answers and diagrams.</div>
                <div>Scoring: per-question cosine similarity against the matching teacher reference answer.</div>
              </div>
            </div>
          </motion.aside>
        </div>
      </main>
    </div>
  )
}
