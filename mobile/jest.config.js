module.exports = {
  preset: undefined,
  transform: {
    '^.+\\.tsx?$': ['babel-jest', { presets: ['@babel/preset-env', '@babel/preset-typescript'] }],
  },
  testEnvironment: 'node',
};
