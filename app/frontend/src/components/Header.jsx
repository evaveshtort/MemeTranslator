import React, { useContext, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { LangContext, AuthContext } from '../App'
import styles from './Header.module.css'

export default function Header() {
  const { lang, toggleLang } = useContext(LangContext)
  const { user, logout } = useContext(AuthContext)
  const navigate = useNavigate()
  const [showHelp, setShowHelp] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  function handleLogout() {
    logout()
    setMenuOpen(false)
    navigate('/')
  }

  const closeMenu = () => setMenuOpen(false)

  return (
    <>
    {showHelp && (
      <div className={styles.modalOverlay} onClick={() => setShowHelp(false)}>
        <div className={styles.modalBox} onClick={e => e.stopPropagation()}>
          <button className={styles.modalClose} onClick={() => setShowHelp(false)}>✕</button>
          <div className={styles.modalTitle}>Как пользоваться сервисом</div>
          <div className={styles.modalBody}>
            <p>Сервис переводит русскоязычные мемы на английский и объясняет их юмор – чтобы поделиться с иностранцами или просто понять контекст.</p>
            <p><strong>Что загружать:</strong> мемы на русском языке с текстом прямо на картинке. Чисто текстовые изображения, скриншоты переписки и мемы без текста не подходят.</p>
            <p><strong>RU / EN</strong> – переключатель языка просмотра. В режиме <strong>RU</strong> показывается оригинал с распознанным текстом. В режиме <strong>EN</strong> – картинка с переведённым текстом и объяснение юмора на английском.</p>
            <p><strong>Поиск</strong> работает по тексту мема, переводу и описанию – можно искать на русском или английском.</p>
            <p><strong>Загрузить</strong> мем можно после регистрации — вкладка «Загрузить» в верхнем меню.</p>
          </div>
        </div>
      </div>
    )}
    <header className={styles.header}>
      <button
        className={styles.burger}
        onClick={() => setMenuOpen(o => !o)}
        aria-label="Меню"
      >
        <span className={`${styles.burgerIcon} ${menuOpen ? styles.burgerOpen : ''}`}>
          <span /><span /><span />
        </span>
      </button>
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
        <div className={styles.helpWrap}>
          <button className={styles.helpBtn} onClick={() => setShowHelp(true)}>?</button>
          <div className={styles.tooltip}>
            RU – оригинал, EN – перевод с объяснением<br/>Нажмите, чтобы открыть подробности
          </div>
        </div>
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
      {menuOpen && (
        <>
          <div className={styles.menuOverlay} onClick={closeMenu} />
          <div className={styles.mobileMenu}>
            <NavLink to="/" end onClick={closeMenu} className={({ isActive }) => isActive ? styles.active : ''}>
              Все мемы
            </NavLink>
            {user && (
              <>
                <NavLink to="/my" onClick={closeMenu} className={({ isActive }) => isActive ? styles.active : ''}>
                  Мои мемы
                </NavLink>
                <NavLink to="/upload" onClick={closeMenu} className={({ isActive }) => isActive ? styles.active : ''}>
                  Загрузить
                </NavLink>
                <div className={styles.menuDivider} />
                <span className={styles.menuEmail}>{user.email}</span>
                <button className={styles.menuLogout} onClick={handleLogout}>Выйти</button>
              </>
            )}
            {!user && (
              <>
                <div className={styles.menuDivider} />
                <NavLink to="/login" onClick={closeMenu} className={({ isActive }) => isActive ? styles.active : ''}>
                  Войти
                </NavLink>
                <NavLink to="/register" onClick={closeMenu} className={({ isActive }) => isActive ? styles.active : ''}>
                  Регистрация
                </NavLink>
              </>
            )}
          </div>
        </>
      )}
    </header>
    </>
  )
}
