import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    files: ["**/*.js"],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: "module",
      globals: {
        process: "readonly",
        console: "readonly",
        fetch: "readonly",
        URL: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    },
  },
  {
    files: ["public/**/*.js"],
    languageOptions: {
      globals: {
        document: "readonly",
        fetch: "readonly",
        window: "readonly",
      },
    },
  },
  {
    ignores: ["node_modules/", "dist/"],
  },
];
