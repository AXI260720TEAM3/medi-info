import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate, useOutletContext } from 'react-router'

const LABEL = { display: 'flex', flexDirection: 'column', gap: 6, fontWeight: 700 }
const ROW = { display: 'flex', gap: 8 }

// 아이디 찾기와 비밀번호 재설정을 한 화면에서 탭으로 나눈다
function FindAccount(){
    const navigate = useNavigate()
    const { user } = useOutletContext()
    const [mode, setMode] = useState('id')   // 'id' 아이디 찾기, 'pw' 비밀번호 재설정
    const [email, setEmail] = useState('')
    const [emailCode, setEmailCode] = useState('')
    const [codeSent, setCodeSent] = useState(false)
    const [cooldown, setCooldown] = useState(0)
    const [password, setPassword] = useState('')
    const [passwordConfirm, setPasswordConfirm] = useState('')
    const [foundId, setFoundId] = useState('')
    const [info, setInfo] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (cooldown <= 0) return
        const timer = setTimeout(() => setCooldown(c => c - 1), 1000)
        return () => clearTimeout(timer)
    }, [cooldown])

    // 탭을 바꾸면 입력한 내용을 비운다 (아이디 찾기용 번호로 비밀번호를 바꿀 수 없기 때문)
    const changeMode = next => {
        setMode(next)
        setEmailCode('')
        setCodeSent(false)
        setCooldown(0)
        setPassword('')
        setPasswordConfirm('')
        setFoundId('')
        setInfo('')
        setError('')
    }

    const handleSendCode = async () => {
        setError('')
        setInfo('')
        try {
            const res = await fetch('/api/auth/email-code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, purpose: mode === 'id' ? 'find_id' : 'reset_pw' }),
            })
            const data = await res.json().catch(() => ({}))
            if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '이메일 주소를 확인해 주세요.')
            setCodeSent(true)
            setCooldown(60)
            // 가입 여부를 알려 주지 않으려고 "가입된 이메일이면"이라고 쓴다
            setInfo('가입된 이메일이면 인증번호를 보냈어요. 10분 안에 입력해 주세요.')
        } catch (err) {
            setError(err.message)
        }
    }

    const handleSubmit = async e => {
        e.preventDefault()
        if (!codeSent) {
            setError('이메일 인증번호를 먼저 받아 주세요.')
            return
        }
        if (mode === 'pw' && password !== passwordConfirm) {
            setError('비밀번호가 서로 달라요.')
            return
        }
        setError('')
        setLoading(true)
        try {
            const res = await fetch(mode === 'id' ? '/api/auth/find-id' : '/api/auth/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(mode === 'id'
                    ? { email: email, email_code: emailCode }
                    : { email: email, email_code: emailCode, password: password }),
            })
            const data = await res.json().catch(() => ({}))
            if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '입력 내용을 확인해 주세요.')
            if (mode === 'id') {
                setFoundId(data.login_id)
                setInfo('')
                setLoading(false)
            } else {
                navigate('/login', { state: { message: '비밀번호를 바꿨어요. 새 비밀번호로 로그인해 주세요.' } })
            }
        } catch (err) {
            setError(err.message)
            setLoading(false)
        }
    }

    if (user) return <Navigate to="/drugs" replace />

    return (
        <form className="card" style={{ maxWidth: 400, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 12 }} onSubmit={handleSubmit}>
            <h1 className="title">계정 찾기</h1>
            <div style={ROW}>
                <button type="button" className={mode === 'id' ? 'btn btn-primary' : 'btn btn-secondary'} style={{ flex: 1 }}
                    onClick={() => changeMode('id')}>아이디 찾기</button>
                <button type="button" className={mode === 'pw' ? 'btn btn-primary' : 'btn btn-secondary'} style={{ flex: 1 }}
                    onClick={() => changeMode('pw')}>비밀번호 재설정</button>
            </div>

            {foundId ? (
                <>
                    <p style={{ margin: 0 }}>가입한 아이디는 <strong>{foundId}</strong> 예요.</p>
                    <Link className="btn btn-primary" to="/login">로그인하러 가기</Link>
                    <button type="button" className="btn btn-secondary" onClick={() => changeMode('pw')}>비밀번호도 잊었어요</button>
                </>
            ) : (
                <>
                    <label style={LABEL}>
                        가입할 때 쓴 이메일
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
                    {mode === 'pw' && (
                        <>
                            <label style={LABEL}>
                                새 비밀번호 (8자 이상)
                                <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)}
                                    autoComplete="new-password" minLength={8} maxLength={72} required />
                            </label>
                            <label style={LABEL}>
                                새 비밀번호 확인
                                <input className="input" type="password" value={passwordConfirm} onChange={e => setPasswordConfirm(e.target.value)}
                                    autoComplete="new-password" required />
                            </label>
                        </>
                    )}
                    {info && <p className="muted" style={{ margin: 0 }}>{info}</p>}
                    {error && <p style={{ margin: 0, color: 'var(--danger-text)' }}>{error}</p>}
                    <button type="submit" className="btn btn-primary" disabled={loading}>
                        {mode === 'id' ? '아이디 찾기' : '비밀번호 바꾸기'}
                    </button>
                </>
            )}
            <p className="muted" style={{ margin: 0 }}><Link to="/login">로그인</Link> · <Link to="/signup">회원가입</Link></p>
        </form>
    )
}
export default FindAccount
