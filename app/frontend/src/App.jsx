import React, { createContext, useContext, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Header from './components/Header'
import MainPage from './pages/MainPage'
import MemePage from './pages/MemePage'
import UploadPage from './pages/UploadPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import MyMemesPage from './pages/MyMemesPage'

export const LangContext = createContext('ru')
export const AuthContext = createContext(null)

function ProtectedRoute({ children }) {
  const { user } = useContext(AuthContext)
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  const [lang, setLang] = useState(() => localStorage.getItem('lang') || 'ru')
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('user')) } catch { return null }
  })

  function toggleLang() {
    const next = lang === 'ru' ? 'en' : 'ru'
    setLang(next)
    localStorage.setItem('lang', next)
  }

  function login(token, userData) {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
  }

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      <LangContext.Provider value={{ lang, toggleLang }}>
        <Header />
        <Routes>
          <Route path="/" element={<MainPage />} />
          <Route path="/memes/:cardId" element={<MemePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
          <Route path="/my" element={<ProtectedRoute><MyMemesPage /></ProtectedRoute>} />
        </Routes>
      </LangContext.Provider>
    </AuthContext.Provider>
  )
}
