import React, { useCallback, useContext, useEffect, useLayoutEffect, useRef, useState } from 'react'
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
  const [queuePosition, setQueuePosition] = useState(null)
  const [processing, setProcessing] = useState(false)

  const imgRef = useRef(null)
  const rightPaneRef = useRef(null)
  const imagePaneRef = useRef(null)

  const adjustLayout = useCallback(() => {
    const img = imgRef.current
    const rightPane = rightPaneRef.current
    const imagePane = imagePaneRef.current

    if (imagePane) imagePane.style.marginLeft = ''
    if (rightPane) rightPane.style.marginLeft = ''

    if (!img || !rightPane) return
    if (window.innerWidth <= 768) return

    const I = img.getBoundingClientRect().width
    const vw = window.innerWidth
    if (I <= 0 || I >= vw / 2) return

    // Layout: [2X] image [X] center [X] text [natural]
    // X = (vw/2 - I) / 3, left margin = 2X = (vw - 2I) / 3
    const twoX = (vw - 2 * I) / 3
    const naturalLeft = imagePane
      ? imagePane.getBoundingClientRect().left
      : img.getBoundingClientRect().left

    if (imagePane) imagePane.style.marginLeft = Math.max(0, Math.round(twoX - naturalLeft)) + 'px'
    // after imagePane shift, rightPane natural left = twoX + I + 16 (gap)
    // desired text left = twoX + I + X = twoX + I + twoX/2 = I + 3X = center + X
    // extra = twoX/2 - 16 = X - 16
    rightPane.style.marginLeft = Math.max(0, Math.round(twoX / 2 - 16)) + 'px'
  }, [])

  useLayoutEffect(() => { adjustLayout() })

  useEffect(() => {
    window.addEventListener('resize', adjustLayout)
    return () => window.removeEventListener('resize', adjustLayout)
  }, [adjustLayout])

  useEffect(() => {
    fetchMeme(cardId).then(data => {
      setMeme(data)
      if (data.status === 'processing' || data.status === 'queued') startSSE()
    }).catch(() => navigate('/'))
  }, [cardId])

  function startSSE() {
    setProcessing(true)
    const es = openEventSource(cardId)
    es.onmessage = (e) => {
      const data = JSON.parse(e.data)
      setCurrentStep(data.current_step)
      if (data.queue_position !== undefined) setQueuePosition(data.queue_position)
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

  async function handleCancel() {
    await deleteMeme(cardId)
    navigate('/')
  }

  async function handleRegenerate() {
    await regenerateMeme(cardId)
    setMeme(prev => ({ ...prev, status: 'queued' }))
    setCurrentStep('queued')
    setQueuePosition(null)
    startSSE()
  }

  if (!meme) return <div className={styles.loading}><div className={styles.spinner} /></div>

  const imgUrl = lang === 'ru' ? meme.original_image_url : meme.result_image_url
  const text = lang === 'ru' ? meme.ocr_full_text : meme.full_text_en
  const explanation = lang === 'ru' ? meme.explanation_ru : meme.explanation_en

  function cleanText(t) {
    if (!t) return t
    return t.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
  }
  const isOwner = user && meme.user_id === user.id

  if (processing) {
    return (
      <div className={styles.page}>
        <div className={`${styles.layout} ${styles.processingLayout}`}>
          {meme.original_image_url && (
            <div className={styles.imagePane} ref={imagePaneRef}>
              <img src={meme.original_image_url} alt="" className={styles.img} ref={imgRef} onLoad={adjustLayout} />
            </div>
          )}
          <div className={styles.processingPane} ref={rightPaneRef}>
            {currentStep === 'queued' ? (
              <div className={styles.progressBox}>
                <div className={styles.queueInfo}>
                  <div className={styles.queueTitle}>В очереди на обработку</div>
                  <div className={styles.queueCount}>
                    {queuePosition === null ? '…' :
                     queuePosition === 0 ? 'Следующий в очереди' :
                     `Заявок впереди: ${queuePosition}`}
                  </div>
                </div>
              </div>
            ) : (
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
            )}
            {currentStep === 'queued' && isOwner && (
              <button className={styles.btnCancel} onClick={handleCancel}>
                Отменить
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (meme.status === 'error') {
    return (
      <div className={styles.page}>
        <div className={styles.content}>
          <div className={styles.errorBox}>
            {meme.original_image_url && (
              <img src={meme.original_image_url} alt="" className={styles.errorThumb} />
            )}
            <div>
              <div className={styles.errorTitle}>Не удалось обработать мем</div>
              <div className={styles.errorDetail}>{formatMemeError(meme)}</div>
            </div>
          </div>
          {isOwner && (
            <div className={styles.actions}>
              <button className={styles.btnRegen} onClick={handleRegenerate}>
                Перегенерировать
              </button>
              <button className={styles.btnDelete} onClick={handleDelete}>
                Удалить
              </button>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.layout}>
        <div className={styles.imagePane} ref={imagePaneRef}>
          {imgUrl && <img src={imgUrl} alt="" className={styles.img} ref={imgRef} onLoad={adjustLayout} />}
        </div>
        <div className={styles.sidebar} ref={rightPaneRef}>
          {text && <p className={styles.text}>{cleanText(text)}</p>}
          {explanation && <p className={styles.explanation}>{cleanText(explanation)}</p>}
          {isOwner && (
            <div className={styles.actions}>
              <button className={styles.btnRegen} onClick={handleRegenerate}>
                Перегенерировать
              </button>
              <button className={styles.btnDelete} onClick={handleDelete}>
                Удалить
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
