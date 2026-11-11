import { useCallback, useEffect, useState } from 'react'
import Badge from '../components/Badge'

// 관리자 운영 탭 (H-5): k8s 상태 보기, backend·web 다시 시작, 사전 다시 적재, 백업과 저장 공간
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

// "5Gi", "512Mi" → MiB
const toMib = (q) => {
  const m = /^(\d+(?:\.\d+)?)(Gi|Mi)$/.exec(q || '')
  return m ? Number(m[1]) * (m[2] === 'Gi' ? 1024 : 1) : null
}
const STALE_HOURS = 36   // 매일 백업이니, 하루 반이 넘게 새 파일이 없으면 놓친 거예요

// 지난번에 꺼진 이유를 한국어로 (k8s가 적는 reason)
const STOP_REASONS = { OOMKilled: '메모리 한도 초과로 강제 종료', Error: '오류로 종료', Completed: '정상 종료' }

// 사용량 막대: 80%를 넘으면 주의색. 한도가 없으면 숫자만
function UsageBar({ used, total, unit, label }) {
  if (used == null) return <span className="muted">-</span>
  const text = unit === 'm' ? `${Math.round(used)}m` : `${Math.round(used)}Mi`
  if (!total) return <span>{text}</span>
  const pct = Math.min(100, (used / total) * 100)
  const totalText = unit === 'm' ? `${(total / 1000).toFixed(total % 1000 ? 1 : 0)}코어` : total >= 1024 ? `${(total / 1024).toFixed(1)}Gi` : `${Math.round(total)}Mi`
  return (
    <div style={{ minWidth: 140 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, fontSize: '0.9rem' }}>
        <span>{text} / {totalText}</span><span className="muted">{pct.toFixed(0)}%</span>
      </div>
      <div role="img" aria-label={`${label} ${pct.toFixed(0)}% 사용`}
        style={{ height: 8, borderRadius: 999, background: 'var(--surface-muted)', overflow: 'hidden', marginTop: 4 }}>
        <div style={{ width: `${Math.max(pct, 1)}%`, height: '100%', background: pct > 80 ? 'var(--caution)' : 'var(--primary)' }} />
      </div>
    </div>
  )
}

// 자원 사용량: metrics-server가 15초쯤마다 재는 값이라 15초마다 다시 불러요 (탭을 떠나면 멈춰요)
function ResourcePanel() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const load = () => call('GET', '/api/admin/ops/resources')
      .then((d) => { setData(d); setError('') })
      .catch((err) => setError(err.message))
    load()
    const timer = setInterval(load, 15000)
    return () => clearInterval(timer)
  }, [])

  return (
    <section className="card">
      <h2>자원 사용량</h2>
      {error && <p style={{ color: 'var(--danger-text)' }}>{error}</p>}
      {!data && !error && <p>불러오는 중...</p>}
      {data && (<>
        {!data.metrics && <p><Badge type="caution">사용량 없음</Badge> metrics-server에서 값을 못 받았어요. k3s를 켠 직후라면 1분쯤 뒤에 다시 보세요.</p>}
        <h3>이 PC (노드)</h3>
        <p className="muted">WSL 전체 값이에요. k8s 밖의 Ollama와 automachine도 같은 WSL을 나눠 써요.</p>
        <div className="table-card">
          <table className="med-table">
            <thead><tr><th>노드</th><th>CPU</th><th>메모리</th></tr></thead>
            <tbody>
              {data.nodes.map(n => (
                <tr key={n.name}>
                  <td>{n.name}</td>
                  <td><UsageBar used={n.cpu_m} total={n.cpu_total_m} unit="m" label="노드 CPU" /></td>
                  <td><UsageBar used={n.mem_mib} total={n.mem_total_mib} unit="Mi" label="노드 메모리" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h3>파드 (한도 대비)</h3>
        <p className="muted">한도(limit)를 넘으면 CPU는 느려지고, 메모리는 k8s가 파드를 끄고 다시 켜요.</p>
        <div className="table-card">
          <table className="med-table">
            <thead><tr><th>파드</th><th>CPU</th><th>메모리</th></tr></thead>
            <tbody>
              {data.pods.map(p => (
                <tr key={p.name}>
                  <td>{p.name}</td>
                  <td><UsageBar used={p.cpu_m} total={p.cpu_limit_m} unit="m" label={`${p.name} CPU`} /></td>
                  <td><UsageBar used={p.mem_mib} total={p.mem_limit_mib} unit="Mi" label={`${p.name} 메모리`} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>)}
    </section>
  )
}

// 백업과 저장 공간: 매일 12:40 db-backup이 backups/에 .dump를 만들고 최근 3개만 남겨요 (k8s/backup.yaml)
function BackupPanel() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    call('GET', '/api/admin/ops/backups')
      .then((d) => { setData(d); setError('') })
      .catch((err) => setError(err.message))
  }, [])
  useEffect(() => { load() }, [load])

  const backupNow = async () => {
    setBusy(true)
    setMessage('')
    try {
      const d = await call('POST', '/api/admin/ops/backup-now')
      setMessage(`${d.job}을(를) 만들었어요. 보통 1분 안에 끝나요.`)
      setTimeout(load, 5000)
    } catch (err) {
      setMessage(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (error) return <section className="card"><h2>백업과 저장 공간</h2><p style={{ color: 'var(--danger-text)' }}>{error}</p></section>
  if (!data) return <section className="card"><h2>백업과 저장 공간</h2><p>불러오는 중...</p></section>

  const newest = data.files[0]
  const ageHours = newest ? (Date.now() - new Date(newest.at)) / 36e5 : null
  const capacity = toMib(data.pvc_capacity)
  const usedPct = capacity ? Math.min(100, (data.db_size_mib / capacity) * 100) : null
  const last = data.last_job

  return (
    <section className="card">
      <h2>백업과 저장 공간</h2>
      {!newest && <p><Badge type="caution">백업 없음</Badge> 아직 백업 파일이 없어요. [지금 백업]으로 하나 만들어 두세요.</p>}
      {newest && ageHours > STALE_HOURS && (
        <p><Badge type="caution">오래됨</Badge> 마지막 백업이 {Math.floor(ageHours)}시간 전이에요. PC나 k3s가 꺼져 있어 예약을 놓쳤을 수 있어요.</p>
      )}
      {last?.state === '실패' && <p><Badge type="caution">실패</Badge> 마지막 백업 작업({last.name})이 실패했어요. 파드 기록을 확인해 주세요.</p>}

      <p className="muted">
        매일 {data.schedule.split(' ').slice(0, 2).reverse().map(n => n.padStart(2, '0')).join(':')}({data.time_zone === 'Asia/Seoul' ? '한국 시간' : data.time_zone || 'UTC'})에
        이 PC의 <code>backups/</code> 폴더에 DB 전체를 복사하고 최근 3개만 남겨요. 계정·내 약·질문 기록이 들어 있어서 저장소에는 올리지 않아요.
      </p>
      <p style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <ConfirmButton label="지금 백업" confirmText="DB 백업을 지금 만들까요?" disabled={busy || data.running} onConfirm={backupNow} />
        <button type="button" className="btn btn-secondary" onClick={load}>새로 보기</button>
        {data.running && <Badge type="notice">백업 진행 중</Badge>}
      </p>
      {message && <p><strong>{message}</strong></p>}

      <div className="table-card">
        <table className="med-table">
          <thead><tr><th>백업 파일</th><th>크기</th><th>만든 시각</th></tr></thead>
          <tbody>
            {data.files.map(f => (
              <tr key={f.name}><td>{f.name}</td><td>{f.size_mib} MB</td><td>{fmt(f.at)}</td></tr>
            ))}
            {data.files.length === 0 && <tr><td colSpan={3}>백업 파일이 없어요.</td></tr>}
          </tbody>
        </table>
      </div>
      {last && <p className="muted">마지막 작업: {last.name} · {last.state}{last.manual ? ' · 손으로 실행' : ''} · {fmt(last.created)}</p>}

      <h3>DB 저장 공간</h3>
      <p>
        <strong>{data.db_size_mib} MB</strong>
        {capacity ? ` / ${data.pvc_capacity} (${usedPct.toFixed(1)}%)` : ''}
      </p>
      {usedPct !== null && (
        <div role="img" aria-label={`DB 저장 공간 ${usedPct.toFixed(1)}% 사용`}
          style={{ height: 10, borderRadius: 999, background: 'var(--surface-muted)', overflow: 'hidden', marginBottom: 12 }}>
          <div style={{ width: `${Math.max(usedPct, 1)}%`, height: '100%', background: usedPct > 80 ? 'var(--caution)' : 'var(--primary)' }} />
        </div>
      )}
      <div className="table-card">
        <table className="med-table">
          <thead><tr><th>큰 표</th><th>크기</th><th>행 수(대략)</th></tr></thead>
          <tbody>
            {data.tables.map(t => (
              <tr key={t.name}><td>{t.name}</td><td>{t.size_mib} MB</td><td>{t.rows.toLocaleString('ko-KR')}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
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

    <ResourcePanel />

    <section className="card">
      <h2>파드</h2>
      <div className="table-card">
        <table className="med-table">
          <thead><tr><th>이름</th><th>상태</th><th>재시작</th><th>지난번 종료</th><th>시작</th></tr></thead>
          <tbody>
            {status.pods.map(p => (
              <tr key={p.name}>
                <td>{p.name}</td>
                <td>{p.phase === 'Succeeded' ? <Badge type="none">끝남</Badge>
                  : p.ready ? <Badge type="notice">정상</Badge> : <Badge type="caution">{p.phase}</Badge>}</td>
                <td>{p.restarts}</td>
                <td>{p.last_stop
                  ? <>{p.last_stop.reason === 'OOMKilled'
                      ? <Badge type="caution">{STOP_REASONS.OOMKilled}</Badge>
                      : (STOP_REASONS[p.last_stop.reason] ?? p.last_stop.reason)}
                    <div className="muted">종료 코드 {p.last_stop.exit_code} · {fmt(p.last_stop.at)}</div></>
                  : '-'}</td>
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

    <BackupPanel />
  </>)
}
export default AdminOps
