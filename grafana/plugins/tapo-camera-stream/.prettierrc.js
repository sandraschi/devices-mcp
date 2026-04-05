module.exports = {
  // Defaults
  semi: true,
  trailingComma: 'es5',
  singleQuote: true,
  printWidth: 100,
  tabWidth: 2,
  useTabs: false,
  bracketSpacing: true,
  jsxBracketSameLine: false,
  arrowParens: 'avoid',
  endOfLine: 'auto',

  // Grafana specific overrides
  overrides: [
    {
      files: '*.{ts,tsx}',
      options: {
        // Match Grafana's TypeScript formatting
        singleQuote: true,
        jsxSingleQuote: false,
        bracketSameLine: false,
        bracketSpacing: true,
      },
    },
  ],
  ...require('@grafana/toolkit/src/config/prettier.plugin.config.json'),
};
