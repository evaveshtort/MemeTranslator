import React, { useEffect, useState } from 'react'
import MasonryGrid from '../components/MasonryGrid'
import MemeCard from '../components/MemeCard'
import SkeletonCard from '../components/SkeletonCard'
import { fetchMemes, searchMemes } from '../api'
import styles from './MainPage.module.css'

export default function MainPage() {
  const [memes, setMemes] = useState([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    if (query.trim()) return
    fetchMemes().then(data => { setMemes(data); setLoading(false) }).catch(() => setLoading(false))
    const interval = setInterval(() => {
      fetchMemes().then(setMemes).catch(console.error)
    }, 5000)
    return () => clearInterval(interval)
  }, [query])

  useEffect(() => {
    if (!query.trim()) {
      setSearchResults(null)
      setSearching(false)
      return
    }
    setSearching(true)
    const timer = setTimeout(() => {
      searchMemes(query)
        .then(data => { setSearchResults(data); setSearching(false) })
        .catch(() => setSearching(false))
    }, 400)
    return () => clearTimeout(timer)
  }, [query])

  const displayed = query.trim() ? (searchResults ?? []) : memes

  return (
    <div>
      <div className={styles.searchBar}>
        <div className={styles.searchWrap}>
          <input
            className={styles.searchInput}
            type="text"
            placeholder="Поиск по мемам…"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
          {query && (
            <button className={styles.clearBtn} onClick={() => setQuery('')}>✕</button>
          )}
        </div>
      </div>
      {loading ? (
        <MasonryGrid>
          {[0, 1, 2].map(i => <SkeletonCard key={i} index={i} />)}
        </MasonryGrid>
      ) : searching ? (
        <div className={styles.spinnerWrap}>
          <div className={styles.spinner} />
        </div>
      ) : displayed.length === 0 ? (
        <div style={{ color: '#555', textAlign: 'center', paddingTop: 100 }}>
          {query.trim() ? 'Ничего не найдено' : 'Нет загруженных мемов'}
        </div>
      ) : (
        <MasonryGrid>
          {displayed.map(m => <MemeCard key={m.card_id} meme={m} />)}
        </MasonryGrid>
      )}
    </div>
  )
}
