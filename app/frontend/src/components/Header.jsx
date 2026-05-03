import React, { useContext } from 'react'
import { NavLink } from 'react-router-dom'
import { LangContext } from '../App'
import styles from './Header.module.css'

export default function Header() {
  const { lang, toggleLang } = useContext(LangContext)

  return (
    <header className={styles.header}>
      <nav className={styles.tabs}>
        <NavLink to="/" end className={({ isActive }) => isActive ? styles.active : ''}>
          Все мемы
        </NavLink>
        <NavLink to="/upload" className={({ isActive }) => isActive ? styles.active : ''}>
          Загрузить
        </NavLink>
      </nav>
      <button className={styles.langToggle} onClick={toggleLang}>
        <span className={lang === 'ru' ? styles.selected : ''}>RU</span>
        <span className={styles.sep}>|</span>
        <span className={lang === 'en' ? styles.selected : ''}>EN</span>
      </button>
    </header>
  )
}
