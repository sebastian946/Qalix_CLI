import path from 'path'

// Extension → { name, framework }
export const EXTENSION_MAP = {
  '.py':    { name: 'Python',     framework: 'pytest' },
  '.js':    { name: 'JavaScript', framework: 'Jest' },
  '.ts':    { name: 'TypeScript', framework: 'Jest + ts-jest' },
  '.go':    { name: 'Go',         framework: 'go test' },
  '.java':  { name: 'Java',       framework: 'JUnit 5' },
  '.rb':    { name: 'Ruby',       framework: 'RSpec' },
  '.php':   { name: 'PHP',        framework: 'PHPUnit' },
  '.cs':    { name: 'C#',         framework: 'xUnit' },
  '.cpp':   { name: 'C++',        framework: 'Google Test' },
  '.rs':    { name: 'Rust',       framework: 'cargo test' },
  '.kt':    { name: 'Kotlin',     framework: 'JUnit 5 + Kotlin' },
  '.swift': { name: 'Swift',      framework: 'XCTest' },
  '.txt':   { name: 'Text',       framework: null },
  '.md':    { name: 'Markdown',   framework: null },
}

// Language name / alias → extension
const ALIAS_MAP = {
  python:     '.py',
  py:         '.py',
  javascript: '.js',
  js:         '.js',
  typescript: '.ts',
  ts:         '.ts',
  go:         '.go',
  golang:     '.go',
  java:       '.java',
  ruby:       '.rb',
  rb:         '.rb',
  php:        '.php',
  csharp:     '.cs',
  cs:         '.cs',
  'c#':       '.cs',
  cpp:        '.cpp',
  'c++':      '.cpp',
  rust:       '.rs',
  rs:         '.rs',
  kotlin:     '.kt',
  kt:         '.kt',
  swift:      '.swift',
}

/**
 * Resolves the language info and the filename to send to the backend.
 *
 * Rules:
 *  - If --lang given → use that extension (override)
 *  - If file has a recognized extension → use it directly
 *  - Otherwise → throw an error asking for --lang
 *
 * @returns {{ name, framework, backendFilename }}
 */
export function resolveLanguage(filename, langOverride) {
  const originalExt = path.extname(filename).toLowerCase()

  if (langOverride) {
    const alias = langOverride.toLowerCase()
    const ext = ALIAS_MAP[alias]

    if (!ext) {
      const supported = [...new Set(Object.keys(ALIAS_MAP))].sort().join(', ')
      throw new Error(
        `Unknown language: "${langOverride}".\nSupported languages: ${supported}`
      )
    }

    const info = EXTENSION_MAP[ext]
    // If the file has no recognized extension, rename it for the backend
    const backendFilename = EXTENSION_MAP[originalExt]
      ? filename
      : path.basename(filename, originalExt) + ext

    return { ...info, backendFilename }
  }

  if (!EXTENSION_MAP[originalExt]) {
    const supported = Object.keys(EXTENSION_MAP).join(', ')
    throw new Error(
      `Extension "${originalExt}" is not supported.\n` +
      `Supported extensions: ${supported}\n` +
      `Use --lang to specify the language manually.`
    )
  }

  return { ...EXTENSION_MAP[originalExt], backendFilename: filename }
}
