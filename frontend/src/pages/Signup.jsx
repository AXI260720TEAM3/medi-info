import { useState } from 'react'
import { Link, Navigate, useNavigate, useOutletContext } from 'react-router'

const LABEL = { display: 'flex', flexDirection: 'column', gap: 6, fontWeight: 700 }
const CHECK = { display: 'flex', alignItems: 'center', gap: 8 }

function Signup(){
    const navigate = useNavigate()
    const {user} = useOutletContext()
    const [loginId, setLoginId] = useState('')
    const [password, setPassword] = useState('')
    const [passwordConfirm, setPasswordConfirm] = useState('')
    const [displayName, setDisplayName] = useState('')
    const [agreePrivacy, setAgreePrivacy] = useState(false)
    const [agreeHealth, setAgreeHealth] = useState(false)
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const handleSubmit = async e => {
        e.preventDefault()
        if(password !== passwordConfirm){
            setError('비밀번호가 서로 달라요.')
            return
        }
        setError('')
        setLoading(true)
        try {
            const res = await fetch('/api/auth/signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    login_id: loginId,
                    display_name: displayName,
                    password: password,
                    agree_privacy: agreePrivacy,
                    agree_health : agreeHealth,
                })
            })
            const data = await res.json().catch(() => ({}))
            if (!res.ok) throw new Error(typeof data.detail === 'string'? data.detail: '입력 내용을 확인해 주세요.')
            navigate('/login', { state: { message: '가입이 끝났어요. 로그인해 주세요.' } })
        } catch (err){
            setError(err.message)
            setLoading(false)
        }
    }

    if (user) return <Navigate to="/drugs" replace />

    return (
        <form className="card" style={{ maxWidth:400, margin: '0 auto', display:'flex', flexDirection: 'column', gap: 12}} onSubmit={handleSubmit}>
            <h1 className="title">회원가입</h1>
            <label style={LABEL}>
                아이디 (4자 이상)
                <input className="input" value={loginId} onChange={e => setLoginId(e.target.value)} minLength={4} maxLength={50} required />
            </label>
            <label style={LABEL}>
                이름 (별명 가능)
                <input className="input" value={displayName} onChange={e => setDisplayName(e.target.value)} maxLength={30} required />
            </label>
            <label style={LABEL}>
                비밀번호 (8자 이상)
                <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} minLength={8} maxLength={72} required />
            </label>
            <label style={LABEL}>
                비밀번호 확인
                <input className="input" type="password" value={passwordConfirm} onChange={e => setPasswordConfirm(e.target.value)} required />
            </label>
            <label style={CHECK}>
                <input type="checkbox" checked={agreePrivacy} onChange={e => setAgreePrivacy(e.target.checked)} required />
                개인정보 수집에 동의해요 (필수)
            </label>
            <label style={CHECK}>
                <input type="checkbox" checked={agreeHealth} onChange={e => setAgreeHealth(e.target.checked)} />
                건강정보(내 약 목록·프로필) 수집에 동의해요 (선택)
            </label>
            <p className="muted" style={{ margin : 0 }}>건강정보에 동의하지 않으면 내 약과 프로필을 저장할 수 없어요.</p>
            <details>
                <summary>개인정보 수집 내용 보기</summary>
                <p className="muted">항목: 아이디, 이름, 비밀번호(암호화 저장). 목적: 회원 식별과 로그인. 보관: 탈퇴할 때까지.</p>
            </details>
            <details>
                <summary>건강정보 수집 내용 보기</summary>
                <p className="muted">항목: 내 약 목록, 프로필(임신·수유·나이 등). 목적: 함께 먹기 점검과 대상별 주의 표시. 보관: 탈퇴할 때까지. 동의하지 않아도 가입할 수 있어요.</p>
            </details>
            {error && <p style={{margin: 0, color: 'var(--danger-text)'}}>{error}</p>}
            <button type="submit" className="btn btn-primary" disabled={loading}>가입하기</button>
            <p className="muted" style={{ margin: 0 }}>이미 계정이 있나요? <Link to="/login">로그인</Link></p>
        </form>
    )
}
export default Signup