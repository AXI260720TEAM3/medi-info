import { Fragment, useEffect, useState } from 'react'
import Badge from '../components/Badge'
import { FIELD_STYLE } from './adminStyles'

// 관리자 계정 탭: 사용자를 찾아 관리자로 승격하거나 해제해요 (routes/admin.py users·change_role)
// 내 권한은 못 바꿔요(서버도 막아요). 바꿀 때는 내 비밀번호를 한 번 더 받아요
const ROLES = [
  { id: 'all', label: '전체' },
  { id: 'admin', label: '관리자' },
  { id: 'user', label: '일반' },
]
const PAGE = 20
const day = (iso) => (iso ? new Date(iso).toLocaleDateString('ko-KR') : '—')
const ROLE_LABEL = { admin: '관리자', user: '일반' }

async function call(url, options) {
  const res = await fetch(url, options)
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : '요청을 처리하지 못했어요.')
  return body
}

// 승격·해제 확인: 표 아래 줄에 펼쳐요. 비밀번호는 이 칸에만 있고 저장하지 않아요
function RoleConfirm({ user, onDone, onCancel }) {
  const next = user.role === 'admin' ? 'user' : 'admin'
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = (e) => {
    e.preventDefault()
    setBusy(true)
    call(`/api/admin/users/${user.user_id}/role`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: next, password }),
    })
      .then(onDone)
      .catch((err) => { setError(err.message); setBusy(false) })
  }

  return (
    <form onSubmit={submit} style={{ padding: 14, border: '1px solid var(--border)', borderRadius: 'var(--radius)', background: 'var(--surface)' }}>
      <p style={{ margin: '0 0 6px' }}>
        <strong>{user.display_name}({user.login_id})</strong>님을 {next === 'admin' ? <strong>관리자로 승격</strong> : <strong>일반 사용자로 해제</strong>}할까요?
      </p>
      <p className="muted" style={{ margin: '0 0 10px' }}>
        {next === 'admin'
          ? '관리자는 모든 질문 기록·사전·운영 탭(다시 시작·백업)을 쓸 수 있고, 다른 사람의 권한도 바꿀 수 있어요.'
          : '다음 요청부터 바로 관리자 화면에 못 들어가요.'}
      </p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <label htmlFor={`pw-${user.user_id}`}>내 비밀번호</label>
        <input id={`pw-${user.user_id}`} type="password" autoComplete="current-password" required autoFocus
          value={password} onChange={(e) => { setPassword(e.target.value); setError('') }} maxLength={128}
          style={{ ...FIELD_STYLE, flex: '0 1 220px' }} />
        <button type="submit" className="btn btn-primary" disabled={busy || !password}>{next === 'admin' ? '승격' : '해제'}</button>
        <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={busy}>취소</button>
      </div>
      {error && <p role="alert" style={{ margin: '10px 0 0', color: 'var(--danger-text)' }}>{error}</p>}
    </form>
  )
}

function AdminUsers() {
  const [role, setRole] = useState('all')
  const [draft, setDraft] = useState('')
  const [q, setQ] = useState('')
  const [offset, setOffset] = useState(0)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null)   // 확인 줄을 펼친 user_id
  const [notice, setNotice] = useState('')
  const [reload, setReload] = useState(0)

  const change = (fn) => (value) => { fn(value); setOffset(0); setEditing(null) }

  useEffect(() => {
    const params = new URLSearchParams({ role, q, limit: PAGE, offset })
    call(`/api/admin/users?${params}`)
      .then((d) => { setData(d); setError('') })
      .catch((err) => setError(err.message))
  }, [role, q, offset, reload])

  const done = (user) => (res) => {
    setEditing(null)
    setNotice(`${user.login_id}: ${ROLE_LABEL[res.role]}(으)로 ${res.changed ? '바꿨어요' : '이미 바뀌어 있었어요'}.`)
    setReload((n) => n + 1)
  }

  return (
    <section className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>계정</h2>
        <span className="muted">이메일은 앞 두 글자만 보여요 · 바꾼 기록은 아래에 남아요</span>
      </div>

      <form role="search" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', margin: '16px 0 12px' }}
        onSubmit={(e) => { e.preventDefault(); change(setQ)(draft.trim()) }}>
        <label htmlFor="user-search" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clipPath: 'inset(50%)' }}>아이디나 이름으로 찾기</label>
        <input id="user-search" type="search" value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={50}
          placeholder="아이디나 이름으로 찾기" style={FIELD_STYLE} />
        <button type="submit" className="btn btn-secondary">찾기</button>
      </form>

      {data && (
        <div role="group" aria-label="권한으로 거르기" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          {ROLES.map(r => (
            <button key={r.id} type="button" aria-pressed={role === r.id} onClick={() => change(setRole)(r.id)}
              className={role === r.id ? 'btn btn-primary' : 'btn btn-secondary'} style={{ borderRadius: 999 }}>
              {r.label} <span style={{ fontWeight: 500 }}>{data.counts[r.id]}</span>
            </button>
          ))}
        </div>
      )}

      {notice && <p role="status"><Badge type="notice">완료</Badge> {notice}</p>}
      {error && <p style={{ color: 'var(--danger-text)' }}>{error}</p>}
      {!data && !error && <p>계정을 불러오는 중...</p>}
      {data && (<>
        {data.items.length === 0 ? <p>조건에 맞는 계정이 없어요.</p> : (
          <div className="table-card">
            <table className="med-table" style={{ minWidth: 760 }}>
              <thead>
                <tr style={{ whiteSpace: 'nowrap' }}><th>아이디</th><th>이름</th><th>이메일</th><th>권한</th><th>가입</th><th>마지막 로그인</th><th style={{ width: 150 }}></th></tr>
              </thead>
              <tbody>
                {data.items.map(u => (
                  <Fragment key={u.user_id}>
                    <tr style={{ borderTop: '1px solid var(--border)', background: editing === u.user_id ? 'var(--primary-bg)' : undefined }}>
                      <td style={{ fontWeight: 500 }}>{u.login_id}</td>
                      <td>{u.display_name}</td>
                      <td className="muted">{u.email ?? '—'}</td>
                      <td style={{ whiteSpace: 'nowrap' }}>{u.role === 'admin' ? <Badge type="notice">관리자</Badge> : <span className="muted">일반</span>}</td>
                      <td className="muted" style={{ whiteSpace: 'nowrap' }}>{day(u.created_at)}</td>
                      <td className="muted" style={{ whiteSpace: 'nowrap' }}>{day(u.last_login_at)}</td>
                      <td className="med-table-action">
                        {u.user_id === data.me ? <Badge type="none">나</Badge> : (
                          <button type="button" className="btn btn-secondary" aria-expanded={editing === u.user_id}
                            onClick={() => { setEditing(editing === u.user_id ? null : u.user_id); setNotice('') }}>
                            {u.role === 'admin' ? '관리자 해제' : '관리자로 승격'}
                          </button>
                        )}
                      </td>
                    </tr>
                    {editing === u.user_id && (
                      <tr style={{ background: 'var(--primary-bg)' }}>
                        <td colSpan={7} style={{ paddingBottom: 16 }}>
                          <RoleConfirm user={u} onDone={done(u)} onCancel={() => setEditing(null)} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <nav aria-label="쪽" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginTop: 12 }}>
          <span className="muted">{data.total ? `${offset + 1}–${Math.min(offset + PAGE, data.total)} / ${data.total}명` : ''}</span>
          <span style={{ display: 'flex', gap: 8 }}>
            <button type="button" className="btn btn-secondary" disabled={offset === 0} onClick={() => setOffset(offset - PAGE)}>이전</button>
            <button type="button" className="btn btn-secondary" disabled={offset + PAGE >= data.total} onClick={() => setOffset(offset + PAGE)}>다음</button>
          </span>
        </nav>

        <h3 style={{ marginTop: 24 }}>최근 권한 변경</h3>
        {data.history.length === 0 ? <p className="muted">아직 바꾼 기록이 없어요.</p> : (
          <ul style={{ margin: 0, paddingLeft: 20, lineHeight: 1.9 }}>
            {data.history.map((h, i) => (
              <li key={i}>
                <span className="muted">{new Date(h.created_at).toLocaleString('ko-KR')}</span>{' '}
                <strong>{h.changed_by_login_id}</strong>님이 <strong>{h.target_login_id}</strong>을(를) {ROLE_LABEL[h.old_role]} → {ROLE_LABEL[h.new_role]}
              </li>
            ))}
          </ul>
        )}
      </>)}
    </section>
  )
}

export default AdminUsers
