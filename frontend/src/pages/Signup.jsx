import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate, useOutletContext } from 'react-router'

const LABEL = { display: 'flex', flexDirection: 'column', gap: 6, fontWeight: 700 }
const CHECK = { display: 'flex', alignItems: 'center', gap: 8 }
const ROW = { display: 'flex', gap: 8 }

function Signup(){
    const navigate = useNavigate()
    const {user} = useOutletContext()
    const [loginId, setLoginId] = useState('')
    const [idChecked, setIdChecked] = useState(false)
    const [password, setPassword] = useState('')
    const [passwordConfirm, setPasswordConfirm] = useState('')
    const [displayName, setDisplayName] = useState('')
    const [email, setEmail] = useState('')
    const [emailCode, setEmailCode] = useState('')
    const [codeSent, setCodeSent] = useState(false)
    const [cooldown, setCooldown] = useState(0)
    const [info, setInfo] = useState('')
    const [agreePrivacy, setAgreePrivacy] = useState(false)
    const [agreeHealth, setAgreeHealth] = useState(false)
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    // 다시 받기까지 남은 초를 1초마다 줄인다
    useEffect(() => {
        if (cooldown <= 0) return
        const timer = setTimeout(() => setCooldown(c => c - 1), 1000)
        return () => clearTimeout(timer)
    }, [cooldown])

    const handleCheckId = async () => {
        setError('')
        setInfo('')
        try {
            const res = await fetch(`/api/auth/check-id?login_id=${encodeURIComponent(loginId)}`)
            const data = await res.json().catch(() => ({}))
            if (!res.ok) throw new Error('아이디는 4자 이상 50자 이하로 입력해 주세요.')
            if (!data.available) throw new Error('이미 사용 중인 아이디예요.')
            setIdChecked(true)
        } catch (err) {
            setIdChecked(false)
            setError(err.message)
        }
    }

    const handleSendCode = async () => {
        setError('')
        setInfo('')
        try {
            const res = await fetch('/api/auth/email-code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, purpose: 'signup' }),
            })
            const data = await res.json().catch(() => ({}))
            if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '이메일 주소를 확인해 주세요.')
            setCodeSent(true)
            setCooldown(60)
            setInfo('인증번호를 보냈어요. 10분 안에 입력해 주세요.')
        } catch (err) {
            setError(err.message)
        }
    }

    const handleSubmit = async e => {
        e.preventDefault()
        if(password !== passwordConfirm){
            setError('비밀번호가 서로 달라요.')
            return
        }
        if(!idChecked){
            setError('아이디 중복확인을 해 주세요.')
            return
        }
        if(!codeSent){
            setError('이메일 인증번호를 먼저 받아 주세요.')
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
                    email: email,
                    email_code: emailCode,
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
                <div style={ROW}>
                    <input className="input" style={{ flex: 1, minWidth: 0 }} value={loginId}
                        onChange={e => { setLoginId(e.target.value); setIdChecked(false) }} minLength={4} maxLength={50} required />
                    <button type="button" className="btn btn-secondary" onClick={handleCheckId} disabled={loginId.length < 4 || idChecked}>
                        {idChecked ? '확인됨' : '중복확인'}
                    </button>
                </div>
            </label>
            {idChecked && <p style={{ margin: 0, color: 'var(--info-text)' }}>사용할 수 있는 아이디예요.</p>}
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
            <label style={LABEL}>
                이메일 (아이디·비밀번호 찾기에 써요)
                <div style={ROW}>
                    <input className="input" style={{ flex: 1, minWidth: 0 }} type="email" value={email}
                        onChange={e => { setEmail(e.target.value); setCodeSent(false); setInfo('') }} maxLength={255} required />
                    <button type="button" className="btn btn-secondary" onClick={handleSendCode} disabled={!email || cooldown > 0}>
                        {cooldown > 0 ? `${cooldown}초` : codeSent ? '다시 받기' : '인증번호 받기'}
                    </button>
                </div>
            </label>
            {codeSent && (
                <label style={LABEL}>
                    인증번호 6자리
                    <input className="input" value={emailCode} onChange={e => setEmailCode(e.target.value.replace(/\D/g, ''))}
                        inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}" maxLength={6} required />
                </label>
            )}
            {info && <p className="muted" style={{ margin: 0 }}>{info}</p>}
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
                <p className="muted">항목: 아이디, 이름, 이메일, 비밀번호(암호화 저장). 목적: 회원 식별, 로그인, 아이디·비밀번호 찾기. 보관: 탈퇴할 때까지.</p>
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
