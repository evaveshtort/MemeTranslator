const BASE = '/api'

export async function fetchMemes() {
  const r = await fetch(`${BASE}/memes`)
  if (!r.ok) throw new Error('Failed to fetch memes')
  return r.json()
}

export async function fetchMeme(cardId) {
  const r = await fetch(`${BASE}/memes/${cardId}`)
  if (!r.ok) throw new Error('Failed to fetch meme')
  return r.json()
}

export async function uploadMeme(file) {
  const form = new FormData()
  form.append('file', file)
  const r = await fetch(`${BASE}/process`, { method: 'POST', body: form })
  if (!r.ok) throw new Error('Upload failed')
  return r.json()
}

export async function searchMemes(q) {
  const r = await fetch(`${BASE}/memes/search?q=${encodeURIComponent(q)}`)
  if (!r.ok) throw new Error('Search failed')
  return r.json()
}

export async function deleteMeme(cardId) {
  const r = await fetch(`${BASE}/memes/${cardId}`, { method: 'DELETE' })
  if (!r.ok) throw new Error('Delete failed')
}

export async function regenerateMeme(cardId) {
  const r = await fetch(`${BASE}/memes/${cardId}/regenerate`, { method: 'POST' })
  if (!r.ok) throw new Error('Regenerate failed')
  return r.json()
}

export function openEventSource(cardId) {
  return new EventSource(`${BASE}/memes/${cardId}/events`)
}
