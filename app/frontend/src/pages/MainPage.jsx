import React, { useEffect, useState } from 'react'
import MasonryGrid from '../components/MasonryGrid'
import MemeCard from '../components/MemeCard'
import { fetchMemes } from '../api'

export default function MainPage() {
  const [memes, setMemes] = useState([])

  useEffect(() => {
    fetchMemes().then(setMemes).catch(console.error)
    const interval = setInterval(() => {
      fetchMemes().then(setMemes).catch(console.error)
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  if (!memes.length) {
    return <div style={{ color: '#555', textAlign: 'center', paddingTop: 100 }}>Нет загруженных мемов</div>
  }

  return (
    <MasonryGrid>
      {memes.map(m => <MemeCard key={m.card_id} meme={m} />)}
    </MasonryGrid>
  )
}
