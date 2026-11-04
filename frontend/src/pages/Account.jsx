import { useEffect, useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router'
import Loading from '../components/Loading'

const CARD = { display: 'flex', flexDirection: 'column', gap: 12 }
const LABEL = { display: 'flex', flexDirection: 'column', gap: 6, fontWeight: 700 }
const CHECK = { display: 'flex', alignItems: 'center', gap: 8 }

function Account() {
    const navigate = useNavigate()
    const { setUser } = useOutletContext()
    const [me, setMe] = useState(undefined)   // undefined: 불러오는 중, null: 로그인 안 함
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
                <button type="submit" className="btn" style={{ background: 'var(--danger)', color: '#fff' }}
                    disabled={!confirmed || loading}>탈퇴하기</button>
            </form>
        </div>
    )
}
export default Account
