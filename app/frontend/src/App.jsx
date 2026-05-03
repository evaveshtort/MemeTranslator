import React, { createContext, useContext, useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import MainPage from './pages/MainPage'
import MemePage from './pages/MemePage'
import UploadPage from './pages/UploadPage'

export const LangContext = createContext('ru')

export default function App() {
  const [lang, setLang] = useState(() => localStorage.getItem('lang') || 'ru')

  function toggleLang() {
    const next = lang === 'ru' ? 'en' : 'ru'
    setLang(next)
    localStorage.setItem('lang', next)
  }

  return (
    <LangContext.Provider value={{ lang, toggleLang }}>
      <Header />
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/memes/:cardId" element={<MemePage />} />
        <Route path="/upload" element={<UploadPage />} />
      </Routes>
    </LangContext.Provider>
  )
}
