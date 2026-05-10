import React, { useEffect, useState } from 'react'
import MasonryGrid from '../components/MasonryGrid'
import MemeCard from '../components/MemeCard'
import { fetchMemes, searchMemes } from '../api'
import styles from './MainPage.module.css'

export default function MainPage() {
  const [memes, setMemes] = useState([])
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState(null)

  useEffect(() => {
    if (query.trim()) return
    fetchMemes().then(setMemes).catch(console.error)
    const interval = setInterval(() => {
      fetchMemes().then(setMemes).catch(console.error)
    }, 5000)
    return () => clearInterval(interval)
  }, [query])

  useEffect(() => {
    if (!query.trim()) {
      setSearchResults(null)
      return
    }
    const timer = setTimeout(() => {
      searchMemes(query).then(setSearchResults).catch(console.error)
    }, 400)
    return () => clearTimeout(timer)
  }, [query])

  const displayed = query.trim() ? (searchResults ?? []) : memes

  return (
    <div>
      <div className={styles.searchBar}>
        <input
          className={styles.searchInput}
          type="text"
          placeholder="Поиск по мемам…"
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
      </div>
      {displayed.length === 0 ? (
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
