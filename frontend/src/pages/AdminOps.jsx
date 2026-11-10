import { useCallback, useEffect, useState } from 'react'
import Badge from '../components/Badge'

// 관리자 운영 탭 (H-5): k8s 상태 보기, backend·web 다시 시작, 사전 다시 적재
// 백엔드 → 운영 API(ops 파드) → k8s API 순서로 가요. compose에서는 503 안내만 보여요
const fmt = (iso) => (iso ? new Date(iso).toLocaleString('ko-KR') : '-')

async function call(method, url) {
  const res = await fetch(url, { method })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '운영 API가 응답하지 않아요.')
  return data
}

// 누르면 바로 하지 않고 "정말 할까요?"를 한 번 더 물어요 (브라우저 confirm 창 대신 화면 안에서)
function ConfirmButton({ label, confirmText, onConfirm, disabled }) {
  const [asking, setAsking] = useState(false)
  if (!asking) {
    return <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => setAsking(true)}>{label}</button>
  }
  return (
    <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
      <span>{confirmText}</span>
      <button type="button" className="btn btn-primary" onClick={() => { setAsking(false); onConfirm() }}>확인</button>
      <button type="button" className="btn btn-secondary" onClick={() => setAsking(false)}>취소</button>
    </span>
  )
}

function AdminOps() {
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    call('GET', '/api/admin/ops/status')
      .then((data) => { setStatus(data); setError('') })
      .catch((err) => setError(err.message))
  }, [])

  useEffect(() => { load() }, [load])

  const act = async (url, done) => {
    setBusy(true)
    setMessage('')
    try {
      const data = await call('POST', url)
      setMessage(done(data))
      setTimeout(load, 3000)   // k8s가 바꾸는 데 시간이 걸려서 3초 뒤 다시 보기
    } catch (err) {
      setMessage(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (error) return <section className="card"><p style={{ color: 'var(--danger-text)' }}>{error}</p></section>
  if (!status) return <p>불러오는 중...</p>

  return (<>
    <section className="card">
      <h2>서비스</h2>
      <p className="muted">
        다시 시작하면 새 파드를 하나씩 띄운 뒤 옛 파드를 꺼요. 잠깐 느려질 수 있지만 끊기지는 않아요.{' '}
        <button type="button" className="btn btn-secondary" onClick={load}>새로 보기</button>
      </p>
      {message && <p><strong>{message}</strong></p>}
      <div className="table-card">
        <table className="med-table">
          <thead><tr><th>이름</th><th>준비</th><th>버전</th><th></th></tr></thead>
          <tbody>
            {status.workloads.map(w => (
              <tr key={w.name}>
                <td>{w.name}</td>
                <td><Badge type={w.ready >= w.want ? 'notice' : 'caution'}>{w.ready}/{w.want}</Badge></td>
                <td>{w.version}</td>
                <td className="med-table-action">
                  {w.restartable && (
                    <ConfirmButton label="다시 시작" confirmText={`${w.name}을(를) 다시 시작할까요?`} disabled={busy}
                      onConfirm={() => act(`/api/admin/ops/restart/${w.name}`, () => `${w.name} 다시 시작을 요청했어요.`)} />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>

    <section className="card">
      <h2>파드</h2>
      <div className="table-card">
        <table className="med-table">
          <thead><tr><th>이름</th><th>상태</th><th>재시작</th><th>시작</th></tr></thead>
          <tbody>
            {status.pods.map(p => (
              <tr key={p.name}>
                <td>{p.name}</td>
                <td>{p.phase === 'Succeeded' ? <Badge type="none">끝남</Badge>
                  : p.ready ? <Badge type="notice">정상</Badge> : <Badge type="caution">{p.phase}</Badge>}</td>
                <td>{p.restarts}</td>
                <td>{fmt(p.started)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>

    <section className="card">
      <h2>사전 적재</h2>
      <p className="muted">
        마지막 배포 때 넣은 CSV를 DB에 다시 넣어요. DB 사전이 비었거나 어긋났을 때 써요.
        CSV를 고쳤다면 PR을 머지하고 다시 배포해야 새 내용이 들어가요.
      </p>
      <ConfirmButton label="사전 다시 적재" confirmText="사전 Job을 새로 돌릴까요?" disabled={busy}
        onConfirm={() => act('/api/admin/ops/dict-reload', (d) => `${d.job}을(를) 만들었어요. 잠시 뒤 아래 목록에서 확인해 주세요.`)} />
      <ul>
        {status.dict_jobs.map(j => <li key={j.name}>{j.name} · {j.state} · 시작 {fmt(j.started)}</li>)}
        {status.dict_jobs.length === 0 && <li>최근 적재 기록이 없어요.</li>}
      </ul>
      <h3>예약 작업</h3>
      <ul>
        {status.cronjobs.map(c => (
          <li key={c.name}>{c.name} · {c.suspend ? '멈춤(설계도 보관용)' : c.schedule} · 마지막 성공 {fmt(c.last)}</li>
        ))}
      </ul>
    </section>
  </>)
}
export default AdminOps
