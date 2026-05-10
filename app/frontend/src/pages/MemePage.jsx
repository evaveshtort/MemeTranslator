import React, { useContext, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { LangContext, AuthContext } from '../App'
import { fetchMeme, deleteMeme, regenerateMeme, openEventSource } from '../api'
import styles from './MemePage.module.css'

const ERROR_STEP_LABELS = {
  ocr: 'OCR',
  remove_text: 'удаление текста',
  caption: 'описание изображения',
  translate: 'перевод',
  s3: 'загрузка файлов',
}

function formatMemeError(meme) {
  const raw = meme.error || ''
  const colonIdx = raw.indexOf(': ')
  const step = colonIdx !== -1 ? raw.slice(0, colonIdx) : ''
  const msg = colonIdx !== -1 ? raw.slice(colonIdx + 2) : raw
  const stepLabel = ERROR_STEP_LABELS[step] || step || 'неизвестный этап'
  const retries =
    step === 'ocr' ? (meme.ocr_retries || 0) :
    step === 'caption' ? (meme.caption_retries || 0) :
    step === 'translate' ? (meme.translation_retries || 0) + (meme.humor_analysis_retries || 0) :
    0
  const retriesStr = retries > 0 ? ` (попыток: ${retries})` : ''
  return `Этап «${stepLabel}»${retriesStr}: ${msg}`
}

const STEP_LABELS = {
  ocr: 'Распознавание текста',
  remove_text: 'Удаление текста',
  caption: 'Описание изображения',
  translate: 'Перевод',
  upload: 'Сохранение файлов',
  done: 'Готово',
  error: 'Ошибка',
}

const STEPS_ORDER = ['ocr', 'remove_text', 'caption', 'translate', 'upload', 'done']

export default function MemePage() {
  const { cardId } = useParams()
  const navigate = useNavigate()
  const { lang } = useContext(LangContext)
  const { user } = useContext(AuthContext)
  const [meme, setMeme] = useState(null)
  const [currentStep, setCurrentStep] = useState(null)
  const [processing, setProcessing] = useState(false)

  useEffect(() => {
    fetchMeme(cardId).then(data => {
      setMeme(data)
      if (data.status === 'processing') startSSE()
    }).catch(() => navigate('/'))
  }, [cardId])

  function startSSE() {
    setProcessing(true)
    const es = openEventSource(cardId)
    es.onmessage = (e) => {
      const data = JSON.parse(e.data)
      setCurrentStep(data.current_step)
      if (data.status === 'success') {
        es.close()
        setProcessing(false)
        fetchMeme(cardId).then(setMeme)
      } else if (data.status === 'error') {
        es.close()
        setProcessing(false)
        fetchMeme(cardId).then(setMeme)
      }
    }
    es.onerror = () => { es.close(); setProcessing(false) }
    return () => es.close()
  }

  async function handleDelete() {
    await deleteMeme(cardId)
    navigate('/')
  }

  async function handleRegenerate() {
    await regenerateMeme(cardId)
    setMeme(prev => ({ ...prev, status: 'processing' }))
    setCurrentStep('ocr')
    startSSE()
  }

  if (!meme) return <div className={styles.loading}><div className={styles.spinner} /></div>

  const imgUrl = lang === 'ru' ? meme.original_image_url : meme.result_image_url
  const text = lang === 'ru' ? meme.ocr_full_text : meme.full_text_en
  const explanation = lang === 'ru' ? meme.explanation_ru : meme.explanation_en

  return (
    <div className={styles.page}>
      <div className={styles.content}>

        {processing ? (
          <div className={styles.progressBox}>
            <div className={styles.steps}>
              {STEPS_ORDER.map(step => (
                <div key={step} className={`${styles.step} ${
                  step === currentStep ? styles.active :
                  STEPS_ORDER.indexOf(step) < STEPS_ORDER.indexOf(currentStep) ? styles.done : ''
                }`}>
                  <div className={styles.dot} />
                  <span>{STEP_LABELS[step]}</span>
                </div>
              ))}
            </div>
          </div>
        ) : meme.status === 'error' ? (
          <div className={styles.errorBox}>
            <div className={styles.errorTitle}>Не удалось обработать мем</div>
            <div className={styles.errorDetail}>{formatMemeError(meme)}</div>
          </div>
        ) : (
          <>
            {imgUrl && <img src={imgUrl} alt="" className={styles.img} />}
            {text && <p className={styles.text}>{text}</p>}
            {explanation && <p className={styles.explanation}>{explanation}</p>}
          </>
        )}

        {user && meme.user_id === user.id && (
          <div className={styles.actions}>
            <button className={styles.btnRegen} onClick={handleRegenerate} disabled={processing}>
              Перегенерировать
            </button>
            <button className={styles.btnDelete} onClick={handleDelete} disabled={processing}>
              Удалить
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
