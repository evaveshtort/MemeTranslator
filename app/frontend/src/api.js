const BASE = '/api'

function getToken() {
  return localStorage.getItem('token')
}

function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function apiFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  })
  if (res.status === 401) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/login'
    throw new Error('Требуется авторизация')
  }
  return res
}

export async function loginUser(email, password) {
  const r = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!r.ok) throw new Error((await r.json()).detail || 'Не удалось войти')
  return r.json()
}

export async function registerUser(email, password) {
  const r = await fetch(`${BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!r.ok) throw new Error((await r.json()).detail || 'Не удалось зарегистрироваться')
  return r.json()
}

export async function fetchMemes() {
  const r = await fetch(`${BASE}/memes`)
  if (!r.ok) throw new Error('Не удалось загрузить список мемов')
  return r.json()
}

export async function fetchMyMemes() {
  const r = await apiFetch(`${BASE}/memes/my`)
  if (!r.ok) throw new Error('Не удалось загрузить ваши мемы')
  return r.json()
}

export async function fetchMeme(cardId) {
  const r = await fetch(`${BASE}/memes/${cardId}`)
  if (!r.ok) throw new Error('Не удалось загрузить мем')
  return r.json()
}

export async function uploadMeme(file) {
  const form = new FormData()
  form.append('file', file)
  const r = await apiFetch(`${BASE}/process`, { method: 'POST', body: form })
  if (!r.ok) throw new Error('Не удалось загрузить изображение')
  return r.json()
}

export async function searchMemes(q) {
  const r = await fetch(`${BASE}/memes/search?q=${encodeURIComponent(q)}`)
  if (!r.ok) throw new Error('Не удалось выполнить поиск')
  return r.json()
}

export async function deleteMeme(cardId) {
  const r = await apiFetch(`${BASE}/memes/${cardId}`, { method: 'DELETE' })
  if (!r.ok) throw new Error('Не удалось удалить мем')
}

export async function regenerateMeme(cardId) {
  const r = await apiFetch(`${BASE}/memes/${cardId}/regenerate`, { method: 'POST' })
  if (!r.ok) throw new Error('Не удалось запустить перегенерацию')
  return r.json()
}

export function openEventSource(cardId) {
  return new EventSource(`${BASE}/memes/${cardId}/events`)
}
