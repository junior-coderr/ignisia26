import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate, useParams } from 'react-router-dom'
import { getQuestionDetail, getStatus, getSummary, uploadStudentPDFs } from '../api'

function scoreColor(score, maxMarks) {
  const ratio = maxMarks > 0 ? score / maxMarks : 0
  if (ratio >= 0.8) return 'var(--correct)'
  if (ratio >= 0.5) return 'var(--partial)'
  return 'var(--incorrect)'
}

export default function DashboardScreen() {
  const { examId } = useParams()
  const navigate = useNavigate()

  const [status, setStatus] = useState('loading')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState(null)
  const [summary, setSummary] = useState(null)
  const [selectedQ, setSelectedQ] = useState(null)
  const [questionData, setQuestionData] = useState(null)
  const [selectedStudent, setSelectedStudent] = useState(null)
  const [studentFiles, setStudentFiles] = useState([])
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const studentFileRef = useRef(null)

  useEffect(() => {
    let intervalId

    const poll = async () => {
      try {
        const { data } = await getStatus(examId)
        setStatus(data.status)
        setProgress(data.progress || 0)
        setError(data.error || null)

        if (data.reference_ready) {
          const summaryResp = await getSummary(examId)
          setSummary(summaryResp.data)
          if (!selectedQ && summaryResp.data.questions?.length) {
            setSelectedQ(summaryResp.data.questions[0].q_number)
          }
        }
      } catch (pollError) {
        console.error(pollError)
        setStatus('error')
        setError('Failed to load exam status')
      }
    }

    poll()
    intervalId = setInterval(poll, 2000)
    return () => clearInterval(intervalId)
  }, [examId, selectedQ])

  useEffect(() => {
    if (!selectedQ) return
    if (!['reference_ready', 'processing_students', 'ready'].includes(status)) return

    const loadQuestion = async () => {
      try {
        const { data } = await getQuestionDetail(examId, selectedQ)
        setQuestionData(data)
        setSelectedStudent((current) => {
          if (current) {
            const stillExists = data.students.find((row) => row.roll_number === current.roll_number)
            if (stillExists) return stillExists
          }
          return data.students[0] || null
        })
      } catch (questionError) {
        console.error(questionError)
        setQuestionData(null)
      }
    }

    loadQuestion()
  }, [examId, selectedQ, status])

  const handleStudentUpload = async () => {
    if (!studentFiles.length) return
    setUploading(true)
    try {
      await uploadStudentPDFs(examId, studentFiles)
      setStudentFiles([])
    } catch (uploadError) {
      console.error(uploadError)
      alert('Student upload failed. Check the backend logs for the extraction error.')
    } finally {
      setUploading(false)
    }
  }

  if (status === 'loading' || status === 'queued' || status === 'processing_reference') {
    const messages = {
      loading: 'Connecting to the grading session…',
      queued: 'Reference sheet queued for processing…',
      processing_reference: 'Extracting teacher answers, question IDs, and full marks…',
    }
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 32 }}>
        <div className="card" style={{ width: '100%', maxWidth: 620, textAlign: 'center', padding: 36 }}>
          <div style={{ fontSize: 58, marginBottom: 16 }}>🧾</div>
          <h2 style={{ marginBottom: 8 }}>{messages[status] || status}</h2>
          <p style={{ marginBottom: 18 }}>The reference answer sheet is being converted into question-level embeddings.</p>
          <div className="progress-bar" style={{ height: 8 }}>
            <div className="progress-fill" style={{ width: `${(progress * 100).toFixed(0)}%` }} />
          </div>
          <p style={{ marginTop: 10, fontSize: '0.84rem' }}>{(progress * 100).toFixed(0)}%</p>
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 32 }}>
        <div className="card" style={{ width: '100%', maxWidth: 620, textAlign: 'center', padding: 36 }}>
          <div style={{ fontSize: 58, marginBottom: 16 }}>⚠️</div>
          <h2 style={{ marginBottom: 8 }}>Processing failed</h2>
          <p style={{ marginBottom: 20 }}>{error || 'The backend could not complete this grading flow.'}</p>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>Back to Reference Upload</button>
        </div>
      </div>
    )
  }

  const questionSummary = summary?.questions?.find((question) => question.q_number === selectedQ)

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 16, background: 'var(--bg-surface)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }} onClick={() => navigate('/')}>
          <div style={{ width: 30, height: 30, borderRadius: 8, background: 'var(--accent)', display: 'grid', placeItems: 'center', fontSize: 14 }}>✓</div>
          <span style={{ fontWeight: 800 }}>GradeSync <span style={{ color: 'var(--accent)' }}>AI</span></span>
        </div>

        <div>
          <div style={{ fontWeight: 700 }}>{summary?.title || 'Reference Answer Key'}</div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            {summary?.exam_code || 'No exam code extracted'} · {summary?.question_count || 0} questions
          </div>
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="badge badge-neutral">{status === 'ready' ? 'Ready' : status === 'processing_students' ? 'Processing Students' : 'Reference Ready'}</span>
          {summary?.total_students > 0 && (
            <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/export/${examId}`)}>
              Export Results
            </button>
          )}
        </div>
      </header>

      {status === 'processing_students' && (
        <div style={{ padding: '12px 24px', borderBottom: '1px solid var(--border)', background: 'rgba(99,102,241,0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span className="spinner" />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Extracting and grading student submissions against the reference sheet…</div>
              <div className="progress-bar" style={{ marginTop: 8 }}>
                <div className="progress-fill" style={{ width: `${(progress * 100).toFixed(0)}%` }} />
              </div>
            </div>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{(progress * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '240px 1fr', minHeight: 0 }}>
        <aside style={{ borderRight: '1px solid var(--border)', padding: '18px 12px', background: 'var(--bg-surface)', overflowY: 'auto' }}>
          <div style={{ fontSize: '0.72rem', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, padding: '0 8px 10px' }}>
            Questions
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {summary?.questions?.map((question) => {
              const active = selectedQ === question.q_number
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
                      <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>{question.max_marks}m</span>
                    </div>
                    <div style={{ fontSize: '0.76rem', marginTop: 4, display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 2, overflow: 'hidden' }}>
                      {question.q_text}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </aside>

        <main style={{ padding: 24, overflowY: 'auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 16, marginBottom: 22 }}>
            {[
              { label: 'Reference Questions', value: summary?.question_count || 0, icon: '📚' },
              { label: 'Student PDFs', value: summary?.total_students || 0, icon: '👥' },
              { label: 'Class Average', value: `${summary?.class_average || 0}/${summary?.max_total || 0}`, icon: '📊' },
              { label: 'Selected Avg', value: questionSummary ? `${questionSummary.avg_score}/${questionSummary.max_marks}` : '—', icon: '🎯' },
            ].map((item) => (
              <div key={item.label} className="card" style={{ padding: 18 }}>
                <div style={{ fontSize: 24, marginBottom: 10 }}>{item.icon}</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--accent-light)' }}>{item.value}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{item.label}</div>
              </div>
            ))}
          </div>

          <div className="card" style={{ padding: 22, marginBottom: 22 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, marginBottom: 14 }}>
              <div>
                <h3 style={{ marginBottom: 4 }}>Upload Student PDFs</h3>
                <p style={{ fontSize: '0.88rem' }}>
                  Page 1 is used for student metadata. Pages 2+ are extracted question-by-question and graded against the reference sheet.
                </p>
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-secondary" onClick={() => studentFileRef.current?.click()}>
                  Browse PDFs
                </button>
                <button className="btn btn-primary" disabled={!studentFiles.length || uploading} onClick={handleStudentUpload}>
                  {uploading ? <><span className="spinner" /> Starting upload…</> : `Grade ${studentFiles.length || ''} Student PDF${studentFiles.length === 1 ? '' : 's'}`}
                </button>
              </div>
            </div>

            <input
              ref={studentFileRef}
              type="file"
              accept=".pdf"
              multiple
              hidden
              onChange={(event) => {
                const pdfs = Array.from(event.target.files || [])
                setStudentFiles((current) => [...current, ...pdfs])
              }}
            />

            <div
              onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault()
                setDragging(false)
                const pdfs = Array.from(event.dataTransfer.files).filter((entry) => entry.name.toLowerCase().endsWith('.pdf'))
                setStudentFiles((current) => [...current, ...pdfs])
              }}
              style={{
                border: `2px dashed ${dragging ? 'var(--accent)' : 'var(--border-light)'}`,
                borderRadius: 'var(--radius-lg)',
                padding: '24px',
                background: dragging ? 'var(--accent-dim)' : 'var(--bg-surface)',
              }}
            >
              <div style={{ fontSize: 34, marginBottom: 10 }}>🗂️</div>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>Drop student answer PDFs here</div>
              <p style={{ fontSize: '0.86rem' }}>You can upload a batch now and upload more later into the same exam.</p>
              {studentFiles.length > 0 && (
                <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {studentFiles.map((file, index) => (
                    <div key={`${file.name}-${index}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: '8px 12px', borderRadius: 10, background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</span>
                      <button className="btn btn-ghost btn-sm" onClick={() => setStudentFiles((current) => current.filter((_, fileIndex) => fileIndex !== index))}>
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {questionData ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1.15fr 0.85fr', gap: 20 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card" style={{ padding: 24 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                    <span className="badge badge-neutral">{questionData.q_number}</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Max marks: {questionData.max_marks}</span>
                    <span style={{ marginLeft: 'auto', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      Attempted by {questionSummary?.students_attempted || 0} student{questionSummary?.students_attempted === 1 ? '' : 's'}
                    </span>
                  </div>
                  <h2 style={{ fontSize: '1.3rem', marginBottom: 10 }}>{questionData.q_text}</h2>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12, marginBottom: 18 }}>
                    <div className="card" style={{ padding: 16, background: 'var(--bg-surface)' }}>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 4 }}>Average similarity</div>
                      <div style={{ fontSize: '1.4rem', fontWeight: 800 }}>{((questionSummary?.avg_similarity || 0) * 100).toFixed(0)}%</div>
                    </div>
                    <div className="card" style={{ padding: 16, background: 'var(--bg-surface)' }}>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 4 }}>Average score</div>
                      <div style={{ fontSize: '1.4rem', fontWeight: 800 }}>{questionSummary?.avg_score || 0}/{questionData.max_marks}</div>
                    </div>
                  </div>

                  <div style={{ fontSize: '0.76rem', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: 10 }}>
                    Reference Answer
                  </div>
                  <div style={{ background: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)', padding: 18, border: '1px solid var(--border)' }}>
                    <p style={{ whiteSpace: 'pre-wrap', color: 'var(--text-primary)' }}>{questionData.reference_answer.text || 'No reference text extracted.'}</p>
                    {questionData.reference_answer.diagram_description && (
                      <div style={{ marginTop: 12, padding: '10px 12px', borderRadius: 10, background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.18)' }}>
                        <strong style={{ color: 'var(--accent-light)' }}>Diagram:</strong> {questionData.reference_answer.diagram_description}
                      </div>
                    )}
                  </div>
                </motion.section>

                <section className="card" style={{ padding: 0, overflow: 'hidden' }}>
                  <div style={{ padding: '18px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h3>Student Results For {questionData.q_number}</h3>
                      <p style={{ fontSize: '0.84rem' }}>Scores are computed from cosine similarity against the matching reference answer.</p>
                    </div>
                    <span className="badge badge-neutral">{questionData.students.length} rows</span>
                  </div>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ background: 'var(--bg-surface)' }}>
                          {['Roll No', 'Name', 'Similarity', 'Score', 'Status'].map((head) => (
                            <th key={head} style={{ textAlign: 'left', padding: '12px 16px', fontSize: '0.76rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
                              {head}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {questionData.students.map((row) => (
                          <tr
                            key={row.roll_number}
                            onClick={() => setSelectedStudent(row)}
                            style={{
                              cursor: 'pointer',
                              background: selectedStudent?.roll_number === row.roll_number ? 'rgba(99,102,241,0.1)' : 'transparent',
                              borderTop: '1px solid var(--border)',
                            }}
                          >
                            <td style={{ padding: '12px 16px' }}><span className="mono">{row.roll_number}</span></td>
                            <td style={{ padding: '12px 16px' }}>{row.name}</td>
                            <td style={{ padding: '12px 16px' }}>{row.attempted ? `${(row.similarity * 100).toFixed(0)}%` : '—'}</td>
                            <td style={{ padding: '12px 16px', color: scoreColor(row.score, row.max_marks), fontWeight: 700 }}>
                              {row.score}/{row.max_marks}
                            </td>
                            <td style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>
                              {row.attempted ? 'Matched by Q ID' : 'Not attempted / not extracted'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                <section className="card" style={{ padding: 24 }}>
                  <div style={{ fontSize: '0.76rem', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: 10 }}>
                    Selected Student Answer
                  </div>
                  {selectedStudent ? (
                    <>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 14 }}>
                        <div>
                          <div style={{ fontWeight: 700 }}>{selectedStudent.name}</div>
                          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{selectedStudent.roll_number}</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Auto grade</div>
                          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: scoreColor(selectedStudent.score, selectedStudent.max_marks) }}>
                            {selectedStudent.score}/{selectedStudent.max_marks}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12, marginBottom: 14 }}>
                        <div className="card" style={{ padding: 16, background: 'var(--bg-surface)' }}>
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 4 }}>Similarity</div>
                          <div style={{ fontWeight: 800, fontSize: '1.25rem' }}>{(selectedStudent.similarity * 100).toFixed(0)}%</div>
                        </div>
                        <div className="card" style={{ padding: 16, background: 'var(--bg-surface)' }}>
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 4 }}>Question linking</div>
                          <div style={{ fontWeight: 700 }}>{selectedStudent.attempted ? 'Matched by question ID' : 'No extracted answer'}</div>
                        </div>
                      </div>

                      <div style={{ background: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)', padding: 18, border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: '0.76rem', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: 10 }}>
                          Student Answer Text
                        </div>
                        <p style={{ whiteSpace: 'pre-wrap', color: 'var(--text-primary)' }}>
                          {selectedStudent.student_answer_text || 'No answer extracted for this question.'}
                        </p>
                        {selectedStudent.student_diagram_description && (
                          <div style={{ marginTop: 12, padding: '10px 12px', borderRadius: 10, background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.18)' }}>
                            <strong style={{ color: 'var(--accent-light)' }}>Diagram:</strong> {selectedStudent.student_diagram_description}
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    <p>No student answers are available for this question yet.</p>
                  )}
                </section>
              </div>
            </div>
          ) : (
            <div className="card" style={{ padding: 28 }}>
              <h3 style={{ marginBottom: 8 }}>Reference is ready</h3>
              <p>Select a question from the left after the reference extraction finishes. Student uploads can start immediately.</p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
