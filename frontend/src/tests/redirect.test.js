import { getSafeRedirectTarget } from '../stores/auth/redirect'

describe('safe internal redirect targets', () => {
  it('keeps a same-origin path and its query and hash', () => {
    expect(getSafeRedirectTarget('/properties/new?draft=1#details')).toBe('/properties/new?draft=1#details')
  })

  it.each([
    ['https://attacker.example/path', null],
    ['//attacker.example/path', null],
    ['/\\\\attacker.example/path', null],
    ['', null],
    [undefined, null],
  ])('rejects unsafe redirect value %s', (value, expected) => {
    expect(getSafeRedirectTarget(value)).toBe(expected)
  })
})
