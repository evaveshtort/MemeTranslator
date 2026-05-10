import React, { useContext } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { LangContext, AuthContext } from '../App'
import styles from './Header.module.css'

export default function Header() {
  const { lang, toggleLang } = useContext(LangContext)
  const { user, logout } = useContext(AuthContext)
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <header className={styles.header}>
      <nav className={styles.tabs}>
        <NavLink to="/" end className={({ isActive }) => isActive ? styles.active : ''}>
          Все мемы
        </NavLink>
        {user && (
          <>
            <NavLink to="/my" className={({ isActive }) => isActive ? styles.active : ''}>
              Мои мемы
            </NavLink>
            <NavLink to="/upload" className={({ isActive }) => isActive ? styles.active : ''}>
              Загрузить
            </NavLink>
          </>
        )}
      </nav>
      <div className={styles.right}>
        <button className={styles.langToggle} onClick={toggleLang}>
          <span className={lang === 'ru' ? styles.selected : ''}>RU</span>
          <span className={styles.sep}>|</span>
          <span className={lang === 'en' ? styles.selected : ''}>EN</span>
        </button>
        {user ? (
          <div className={styles.userMenu}>
            <span className={styles.email}>{user.email}</span>
            <button className={styles.logoutBtn} onClick={handleLogout}>Выйти</button>
          </div>
        ) : (
          <div className={styles.authLinks}>
            <NavLink to="/login" className={({ isActive }) => isActive ? styles.active : ''}>Войти</NavLink>
            <NavLink to="/register" className={({ isActive }) => isActive ? styles.active : ''}>Регистрация</NavLink>
          </div>
        )}
      </div>
    </header>
  )
}
