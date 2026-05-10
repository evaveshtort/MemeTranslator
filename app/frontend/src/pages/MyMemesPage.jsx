import React, { useEffect, useState } from 'react'
import MasonryGrid from '../components/MasonryGrid'
import MemeCard from '../components/MemeCard'
import { fetchMyMemes, deleteMeme } from '../api'
import styles from './MainPage.module.css'

const STEP_LABELS = {
  ocr: 'OCR',
  remove_text: 'удаление текста',
  caption: 'описание изображения',
  translate: 'перевод',
  s3: 'загрузка файлов',
}

function formatError(meme) {
  const raw = meme.error || ''
  const colonIdx = raw.indexOf(': ')
  const step = colonIdx !== -1 ? raw.slice(0, colonIdx) : ''
  const msg = colonIdx !== -1 ? raw.slice(colonIdx + 2) : raw

  const stepLabel = STEP_LABELS[step] || step || 'неизвестный этап'

  const retries =
    step === 'ocr' ? (meme.ocr_retries || 0) :
    step === 'caption' ? (meme.caption_retries || 0) :
    step === 'translate' ? (meme.translation_retries || 0) + (meme.humor_analysis_retries || 0) :
    0

  const retriesStr = retries > 0 ? ` (попыток: ${retries})` : ''
  return `Ошибка на этапе «${stepLabel}»${retriesStr}: ${msg}`
}

export default function MyMemesPage() {
  const [memes, setMemes] = useState([])

  useEffect(() => {
    fetchMyMemes().then(setMemes).catch(console.error)
    const interval = setInterval(() => {
      fetchMyMemes().then(setMemes).catch(console.error)
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const errors = memes.filter(m => m.status === 'error')
  const active = memes.filter(m => m.status !== 'error')

  async function dismissError(cardId) {
    await deleteMeme(cardId).catch(console.error)
    setMemes(prev => prev.filter(m => m.card_id !== cardId))
  }

  return (
    <div style={{ paddingTop: 52 }}>
      {errors.length > 0 && (
        <div className={styles.errorBanner}>
          <div className={styles.errorBannerTitle}>Ошибки обработки</div>
          {errors.map(e => (
            <div key={e.card_id} className={styles.errorItem}>
              <span className={styles.errorText}>{formatError(e)}</span>
              <button className={styles.errorDismiss} onClick={() => dismissError(e.card_id)}>✕</button>
            </div>
          ))}
        </div>
      )}
      {active.length === 0 ? (
        <div style={{ color: '#555', textAlign: 'center', paddingTop: 100 }}>
          Вы ещё не загружали мемы
        </div>
      ) : (
        <MasonryGrid>
          {active.map(m => <MemeCard key={m.card_id} meme={m} />)}
        </MasonryGrid>
      )}
    </div>
  )
}
