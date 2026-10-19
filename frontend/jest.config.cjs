module.exports = {
  testEnvironment: 'node',
  testMatch: ['<rootDir>/src/**/*.test.js'],
  transform: { '^.+\\.js$': 'babel-jest' },
  clearMocks: true,
}
