import js from '@eslint/js'
import ts from 'typescript-eslint'
import vue from 'eslint-plugin-vue'
import globals from 'globals'

export default ts.config(
  {
    ignores: ['dist/**', 'node_modules/**', 'coverage/**', 'playwright-report/**'],
  },
  js.configs.recommended,
  ...ts.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    files: ['**/*.{js,ts,tsx,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
      },
      parserOptions: {
        parser: ts.parser,
        extraFileExtensions: ['.vue'],
      },
    },
    rules: {
      // Unused variables are already enforced by `vue-tsc` (noUnusedLocals /
      // noUnusedParameters); keep eslint's copy in sync with the TS convention
      // that an underscore prefix marks a deliberately unused binding.
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
      // `App` is the conventional name for the root single-file component.
      'vue/multi-word-component-names': ['error', { ignores: ['App'] }],

      // Template *formatting* rules from vue/recommended are turned off: they
      // are purely cosmetic and enabling them would rewrite several hundred
      // lines of otherwise-working markup for no behavioural gain. Everything
      // else in vue/recommended (correctness and API-usage rules) stays on.
      'vue/attributes-order': 'off',
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
    },
  },
)
