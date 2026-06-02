import React, { useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { LangContext } from '../App'
import styles from './MemeCard.module.css'

const STEP_LABELS = {
  queued: 'В очереди…',
  ocr: 'Распознавание текста…',
  remove_text: 'Удаление текста…',
  caption: 'Описание изображения…',
  translate: 'Перевод…',
  upload: 'Сохранение…',
  error: 'Ошибка',
}

export default function MemeCard({ meme }) {
  const { lang } = useContext(LangContext)
  const navigate = useNavigate()

  const isProcessing = meme.status === 'processing' || meme.status === 'queued'
  const isError = meme.status === 'error'
  const imgUrl = lang === 'ru' ? meme.original_image_url : meme.result_image_url

  return (
    <div className={styles.card} onClick={() => navigate(`/memes/${meme.card_id}`)}>
      {isProcessing || isError || !imgUrl ? (
        <div className={styles.placeholder}>
          {isError
            ? <span className={styles.errorLabel}>Ошибка</span>
            : <>
                <div className={styles.spinner} />
                <span className={styles.stepLabel}>
                  {STEP_LABELS[meme.current_step] || 'Обработка…'}
                </span>
              </>
          }
        </div>
      ) : (
        <img src={imgUrl} alt="" className={styles.img} />
      )}
    </div>
  )
}
