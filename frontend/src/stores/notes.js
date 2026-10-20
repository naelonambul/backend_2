export const SHORT_NOTE_LIMIT = 140
export const RECENT_NOTE_LIMIT = 6

export function getExcerpt(contents = '', limit = 126) {
  const text = String(contents).trim()
  return text.length > limit ? text.slice(0, limit).trimEnd() + '…' : text
}

export function getCollectionCounts(notes = []) {
  return {
    all: notes.length,
    recent: Math.min(notes.length, RECENT_NOTE_LIMIT),
    short: notes.filter((note) => String(note.contents ?? '').trim().length <= SHORT_NOTE_LIMIT).length,
    long: notes.filter((note) => String(note.contents ?? '').trim().length > SHORT_NOTE_LIMIT).length,
  }
}

export function filterNotes(notes = [], query = '', collection = 'all') {
  const needle = query.trim().toLocaleLowerCase('ko-KR')
  const ordered = [...notes].sort((a, b) => Number(b.idx) - Number(a.idx))
  const matching = ordered.filter((note) => {
    const text = String(note.title ?? '') + ' ' + String(note.contents ?? '')
    if (needle && !text.toLocaleLowerCase('ko-KR').includes(needle)) return false

    const size = String(note.contents ?? '').trim().length
    if (collection === 'short') return size <= SHORT_NOTE_LIMIT
    if (collection === 'long') return size > SHORT_NOTE_LIMIT
    return true
  })

  return collection === 'recent' ? matching.slice(0, RECENT_NOTE_LIMIT) : matching
}

export function noteTone(idx) {
  const tones = ['mint', 'butter', 'blue', 'lilac']
  const numericIndex = Number(idx) || 0
  return tones[Math.abs(numericIndex) % tones.length]
}
