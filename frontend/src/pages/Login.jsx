import { useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router'

function Login() {
    const navigate = useNavigate()
    const {setUser} = useOutletContext()
    const [loginId, setLoginId] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const handleSubmit = async e => {
        e.preventDefault()
        setError('')
        setLoading(true)
        try {
            const res = await fetch('/api/auth/login', {
                method : 'POST',
                headers : { 'Content-Type': 'application/json' },
                body: JSON.stringify( { login_id: loginId, password: password }),
            })
            const data = await res.json()
            if(!res.ok) throw new Error(data.detail)
            setUser(data)
            navigate('/drugs')
        } catch (err){
            setError(err.message)
            setLoading(false)
        }
    }

    return (
        <form className="card" style={{ maxWidth: 400, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 12}}
         onSubmit={handleSubmit}>
            <h1 className="title">로그인</h1>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontWeight: 700}}>
                아이디
                <input className="input" value={loginId} onChange={e => setLoginId(e.target.value)} required />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontWeight: 700}}>
                비밀번호
                <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value) } required />
            </label>
            {error && <p style={{ margin: 0, color: 'var(--danger-text)' }}>{error}</p>}
            <button type="submit" className="btn btn-primary" disabled={loading}>로그인</button>
            <p className="muted" style={{margin: 0}}>처음이신가요? <Link to="/signup">회원가입</Link></p>
         </form>
    )
}
export default Login