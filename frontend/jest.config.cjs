module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/src/**/*.test.js'],
  transform: { '^.+\\.js$': 'babel-jest' },
  clearMocks: true,
}
