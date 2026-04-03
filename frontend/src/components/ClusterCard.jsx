const TYPE_COLORS = {
  correct:   { color: 'var(--correct)',   bg: 'var(--correct-bg)',   label: 'Correct' },
  partial:   { color: 'var(--partial)',   bg: 'var(--partial-bg)',   label: 'Partial' },
  incorrect: { color: 'var(--incorrect)', bg: 'var(--incorrect-bg)', label: 'Incorrect' },
  edge_case: { color: 'var(--edge)',      bg: 'var(--edge-bg)',      label: 'Edge Case' },
}

const TYPE_ICON = { correct: '✅', partial: '⚠️', incorrect: '❌', edge_case: '🔮' }

function highlightKeywords(text, keywords) {
  if (!keywords?.length || !text) return text
  const escaped = keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const regex = new RegExp(`(${escaped.join('|')})`, 'gi')
  const parts = text.split(regex)
  return parts.map((p, i) =>
    regex.test(p)
      ? <mark key={i} className="kw-highlight">{p}</mark>
      : p
  )
}

export default function ClusterCard({ cluster, maxMarks, onOpen, rubricKeywords = [] }) {
  const tc = TYPE_COLORS[cluster.type] || TYPE_COLORS.partial
  const icon = TYPE_ICON[cluster.type] || '📌'
  const rep = cluster.representative
  const previewText = rep?.answer?.text || rep?.combined_text || ''

  return (
    <div
      onClick={onOpen}
      style={{
        background: 'var(--bg-card)',
        border: `1px solid ${cluster.graded ? tc.color + '55' : 'var(--border)'}`,
        borderRadius: 'var(--radius-lg)',
        padding: 20,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.borderColor = tc.color + '80' }}
      onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.borderColor = cluster.graded ? tc.color + '55' : 'var(--border)' }}
    >
      {/* Graded ribbon */}
      {cluster.graded && (
        <div style={{ position: 'absolute', top: 12, right: 12, background: 'var(--correct)', color: '#fff',
          fontSize: '0.68rem', fontWeight: 700, padding: '2px 10px', borderRadius: 999, letterSpacing: '0.06em' }}>
          ✓ GRADED {cluster.score}/{maxMarks}
        </div>
      )}

      {/* Top: type + count */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 12 }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, background: tc.bg,
          display: 'grid', placeItems: 'center', fontSize: 18, flexShrink: 0 }}>
          {icon}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: tc.color,
              textTransform: 'uppercase', letterSpacing: '0.06em' }}>{tc.label}</span>
          </div>
          <h4 style={{ fontSize: '0.875rem', lineHeight: 1.3, marginTop: 2,
            overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
            {cluster.label}
          </h4>
        </div>
      </div>

      {/* Student count */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span style={{ fontWeight: 800, fontSize: '1.75rem', color: tc.color, lineHeight: 1 }}>
          {cluster.student_count}
        </span>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          student{cluster.student_count !== 1 ? 's' : ''}
        </span>
        {cluster.suggested_score != null && !cluster.graded && (
          <span style={{ marginLeft: 'auto', fontSize: '0.78rem', color: 'var(--text-muted)',
            background: 'var(--bg-surface)', padding: '2px 8px', borderRadius: 6, border: '1px solid var(--border)' }}>
            AI suggests: {cluster.suggested_score}/{maxMarks}
          </span>
        )}
      </div>

      {/* Answer preview */}
      {previewText && (
        <div style={{ background: 'var(--bg-surface)', borderRadius: 8, padding: '10px 12px',
          fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 12,
          display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          "{previewText.replace('[Text]: ', '').substring(0, 180)}…"
        </div>
      )}

      {/* Keywords matched */}
      {cluster.matched_keywords?.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 12 }}>
          {cluster.matched_keywords.slice(0, 4).map(kw => (
            <span key={kw} className="badge" style={{ background: 'rgba(99,102,241,0.12)', color: 'var(--accent-light)', fontSize: '0.68rem' }}>
              ✓ {kw}
            </span>
          ))}
        </div>
      )}

      {/* Keyword match bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div className="progress-bar" style={{ flex: 1, height: 4 }}>
          <div style={{ height: '100%', borderRadius: 999, transition: 'width 0.5s ease',
            width: `${(cluster.keyword_match_pct * 100).toFixed(0)}%`,
            background: `linear-gradient(90deg, ${tc.color}, ${tc.color}88)` }} />
        </div>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          {(cluster.keyword_match_pct * 100).toFixed(0)}% keywords
        </span>
      </div>

      {/* CTA */}
      <div style={{ marginTop: 14, display: 'flex', justifyContent: 'flex-end' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--accent-light)', fontWeight: 600 }}>
          {cluster.graded ? 'View / Edit →' : 'Grade this cluster →'}
        </span>
      </div>
    </div>
  )
}
