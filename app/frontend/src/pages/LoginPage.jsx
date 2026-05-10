import React, { useContext, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthContext } from '../App'
import { loginUser } from '../api'
import styles from './LoginPage.module.css'

export default function LoginPage() {
  const { login } = useContext(AuthContext)
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { token, user } = await loginUser(email, password)
      login(token, user)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <form className={styles.box} onSubmit={handleSubmit}>
        <h1 className={styles.title}>Войти</h1>
        {error && <div className={styles.error}>{error}</div>}
        <div className={styles.field}>
          <label className={styles.label}>Email</label>
          <input className={styles.input} type="email" value={email}
            onChange={e => setEmail(e.target.value)} required autoFocus />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Пароль</label>
          <input className={styles.input} type="password" value={password}
            onChange={e => setPassword(e.target.value)} required />
        </div>
        <button className={styles.btn} disabled={loading}>
          {loading ? 'Вхожу…' : 'Войти'}
        </button>
        <div className={styles.footer}>
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </div>
      </form>
    </div>
  )
}
