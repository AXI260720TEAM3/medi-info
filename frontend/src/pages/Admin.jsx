import { useState } from 'react'
import AdminChatLogs from './AdminChatLogs'
import AdminDict from './AdminDict'
import AdminDashboard from './AdminDashboard'
import AdminOps from './AdminOps'
import AdminUsers from './AdminUsers'

// 관리자 화면 (기능명세 H). 관리자인지는 서버가 확인해요 (화면은 받은 오류를 보여 줄 뿐)
// 탭을 하나씩 채워 가요: H-1 질문 기록 → H-2 사전 → H-4 대시보드 → H-5 운영
const TABS = [
  { id: 'logs', label: '질문 기록', ready: true },
  { id: 'dict', label: '사전', ready: true },
  { id: 'dashboard', label: '대시보드', ready: true },
  { id: 'ops', label: '운영', ready: true },
  { id: 'users', label: '계정', ready: true },
]

function Admin() {
  const [tab, setTab] = useState('logs')

  return (
    <section>
      <h1 className="title">관리자</h1>
      <div className="admin-tabs" role="tablist">
        {TABS.map(t => (
          <button key={t.id} type="button" role="tab" aria-selected={tab === t.id}
            className={tab === t.id ? 'btn btn-primary' : 'btn btn-secondary'}
            disabled={!t.ready} onClick={() => setTab(t.id)}>
            {t.label}{!t.ready && ' (준비 중)'}
          </button>
        ))}
      </div>
      {tab === 'logs' && <AdminChatLogs />}
      {tab === 'dict' && <AdminDict />}
      {tab === 'dashboard' && <AdminDashboard />}
      {tab === 'ops' && <AdminOps />}
      {tab === 'users' && <AdminUsers />}
    </section>
  )
}
export default Admin
