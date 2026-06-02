import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadMeme } from '../api'
import styles from './UploadPage.module.css'

export default function UploadPage() {
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef()
  const navigate = useNavigate()

  async function handleFile(file) {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const { card_id } = await uploadMeme(file)
      navigate(`/memes/${card_id}`)
    } catch (e) {
      setError('Ошибка загрузки. Попробуйте ещё раз.')
      setLoading(false)
    }
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  return (
    <div className={styles.page}>
      <div
        className={`${styles.dropzone} ${dragging ? styles.over : ''}`}
        onClick={() => !loading && inputRef.current.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={e => handleFile(e.target.files[0])}
        />
        {loading
          ? <><div className={styles.spinner} /><span>Загружаем…</span></>
          : <><span className={styles.icon}>↑</span><span>Нажмите или перетащите файл</span></>
        }
      </div>
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.hint}>
        <p>Загружайте мемы на русском языке с текстом прямо на картинке.</p>
        <p>Чисто текстовые изображения и мемы без текста не поддерживаются.</p>
      </div>
    </div>
  )
}
