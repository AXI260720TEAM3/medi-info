import { useEffect, useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router'
import Loading from '../components/Loading'

const CARD = { display: 'flex', flexDirection: 'column', gap: 12 }
const LABEL = { display: 'flex', flexDirection: 'column', gap: 6, fontWeight: 700 }
const CHECK = { display: 'flex', alignItems: 'center', gap: 8 }
const DANGER_BTN = { background: 'var(--danger)', color: '#fff' }

function Account() {
    const navigate = useNavigate()
    const { setUser } = useOutletContext()
    const [me, setMe] = useState(undefined)   // undefined: 불러오는 중, null: 로그인 안 함

    // 건강정보 동의
    const [withdrawConfirmed, setWithdrawConfirmed] = useState(false)
    const [consentError, setConsentError] = useState('')
    const [consentLoading, setConsentLoading] = useState(false)

    // 회원 탈퇴
    const [password, setPassword] = useState('')
    const [confirmed, setConfirmed] = useState(false)
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        fetch('/api/auth/me')
            .then(res => (res.ok ? res.json() : null))
            .then(data => setMe(data))
            .catch(() => setMe(null))
    }, [])

    // 동의(POST)와 철회(DELETE)는 주소가 같고 방법만 달라요
    const handleConsent = async method => {
        setConsentError('')
        setConsentLoading(true)
        try {
            const res = await fetch('/api/auth/consent/health', { method: method })
            const data = await res.json().catch(() => ({}))
            if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '처리하지 못했어요. 잠시 후 다시 시도해 주세요.')
            setMe(data)
            setUser(data)
            setWithdrawConfirmed(false)
        } catch (err) {
            setConsentError(err.message)
        }
        setConsentLoading(false)
    }

    const handleDelete = async e => {
        e.preventDefault()
        setError('')
        setLoading(true)
        try {
            const res = await fetch('/api/auth/me', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: password }),
            })
            const data = await res.json().catch(() => ({}))
            if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '탈퇴하지 못했어요. 잠시 후 다시 시도해 주세요.')
            setUser(null)   // 위쪽 메뉴도 로그아웃 상태로
            navigate('/drugs', { replace: true })
        } catch (err) {
            setError(err.message)
            setLoading(false)
        }
    }

    if (me === undefined) return <Loading />
    if (me === null) return <p>내 정보는 로그인하면 볼 수 있어요. <Link to="/login">로그인하기</Link></p>

    return (
        <div style={{ maxWidth: 400, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
            <section className="card" style={CARD}>
                <h1 className="title">내 정보</h1>
                <p style={{ margin: 0 }}>아이디: {me.login_id}</p>
                <p style={{ margin: 0 }}>이름: {me.display_name}</p>
            </section>

            <section className="card" style={CARD}>
                <h2 style={{ margin: 0 }}>건강정보 수집 동의</h2>
                <p style={{ margin: 0 }}>
                    지금 상태: <strong>{me.agree_health ? '동의함' : '동의하지 않음'}</strong>
                </p>
                <details>
                    <summary>건강정보 수집 내용 보기</summary>
                    <p className="muted">항목: 내 약 목록, 프로필(임신·수유·나이 등). 목적: 함께 먹기 점검과 대상별 주의 표시. 보관: 동의를 철회하거나 탈퇴할 때까지.</p>
                </details>
                {me.agree_health ? (<>
                    <p className="muted" style={{ margin: 0 }}>
                        동의를 철회하면 저장한 내 약 목록과 프로필이 바로 지워지고 되돌릴 수 없어요.
                    </p>
                    <label style={CHECK}>
                        <input type="checkbox" checked={withdrawConfirmed} onChange={e => setWithdrawConfirmed(e.target.checked)} />
                        내 약 목록과 프로필이 지워지는 것을 확인했어요
                    </label>
                    {consentError && <p style={{ margin: 0, color: 'var(--danger-text)' }}>{consentError}</p>}
                    <button type="button" className="btn" style={DANGER_BTN}
                        onClick={() => handleConsent('DELETE')} disabled={!withdrawConfirmed || consentLoading}>동의 철회</button>
                </>) : (<>
                    <p className="muted" style={{ margin: 0 }}>
                        동의하면 내 약을 저장하고 함께 먹기 점검을 쓸 수 있어요.
                    </p>
                    {consentError && <p style={{ margin: 0, color: 'var(--danger-text)' }}>{consentError}</p>}
                    <button type="button" className="btn btn-primary"
                        onClick={() => handleConsent('POST')} disabled={consentLoading}>동의하기</button>
                </>)}
            </section>

            <form className="card" style={CARD} onSubmit={handleDelete}>
                <h2 style={{ margin: 0 }}>회원 탈퇴</h2>
                <p className="muted" style={{ margin: 0 }}>
                    탈퇴하면 계정, 내 약 목록, 건강 프로필, 동의 기록이 바로 지워지고 되돌릴 수 없어요.
                    AI 질문 기록은 누구의 것인지 알 수 없게 바꿔서 남겨요.
                </p>
                <label style={LABEL}>
                    비밀번호 확인
                    <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)}
                        autoComplete="current-password" required />
                </label>
                <label style={CHECK}>
                    <input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />
                    위 내용을 확인했어요
                </label>
                {error && <p style={{ margin: 0, color: 'var(--danger-text)' }}>{error}</p>}
                <button type="submit" className="btn" style={DANGER_BTN}
                    disabled={!confirmed || loading}>탈퇴하기</button>
            </form>
        </div>
    )
}
export default Account
