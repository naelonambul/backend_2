import { filterNotes, getCollectionCounts, getExcerpt, noteTone, SHORT_NOTE_LIMIT } from '../stores/notes'

const notes = [
  { idx: 2, title: '바다', contents: '파도 소리를 오래 들었다.' },
  { idx: 5, title: '아이디어', contents: '작은 메모' },
  { idx: 3, title: '읽을거리', contents: 'x'.repeat(SHORT_NOTE_LIMIT + 1) },
]

describe('note discovery helpers', () => {
  it('searches both titles and contents and sorts newest first', () => {
    expect(filterNotes(notes, '메모').map((note) => note.idx)).toEqual([5])
    expect(filterNotes(notes).map((note) => note.idx)).toEqual([5, 3, 2])
  })

  it('filters short and long notes from their actual content', () => {
    expect(filterNotes(notes, '', 'short').map((note) => note.idx)).toEqual([5, 2])
    expect(filterNotes(notes, '', 'long').map((note) => note.idx)).toEqual([3])
  })

  it('limits the recent collection and reports collection counts', () => {
    const many = Array.from({ length: 8 }, (_, index) => ({ idx: index + 1, title: '기록', contents: '메모' }))
    expect(filterNotes(many, '', 'recent')).toHaveLength(6)
    expect(getCollectionCounts(notes)).toEqual({ all: 3, recent: 3, short: 2, long: 1 })
  })

  it('shortens long excerpts and assigns a stable cover tone', () => {
    expect(getExcerpt(' 한 문장 ')).toBe('한 문장')
    expect(getExcerpt('x'.repeat(130))).toHaveLength(127)
    expect(noteTone(4)).toBe('mint')
  })
})
