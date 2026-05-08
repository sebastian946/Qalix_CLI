# Qalix CLI

Command-line tool to analyze source code and automatically generate tests using AI.

---

## Requirements

- Node.js 18 or higher
- Qalix backend running (local or remote)

---

## Installation

```bash
cd cli
npm install
npm link          # registers "qalix" as a global command
```

Verify the installation:

```bash
qalix --version
qalix --help
```

To uninstall the global command:

```bash
npm unlink -g qalix-cli
```

---

## Usage

```bash
qalix analyze <file> [options]
```

### Options

| Option              | Description                                      | Default               |
| ------------------- | ------------------------------------------------ | --------------------- |
| `-l, --lang <lang>` | Programming language (see supported list below)  | Detected by extension |
| `-u, --url <url>`   | Qalix backend URL                                | http://localhost:8000 |
| `-o, --output <f>`  | Save generated tests to a file                   | Prints to stdout only |

### Examples

```bash
# Automatically detects Python from the .py extension
qalix analyze src/calculator.py

# Automatically detects JavaScript from .js
qalix analyze app.js

# Override language when the file has no recognized extension
qalix analyze mycode --lang go

# Save generated tests to a file
qalix analyze calculator.py --output tests/test_calculator.py

# Remote backend
qalix analyze app.ts --url https://api.qalix.com

# All options combined
qalix analyze service.java --lang java --output ServiceTest.java --url http://localhost:8000
```

---

## Supported Languages

| `--lang`         | Extension | Generated test framework   |
| ---------------- | --------- | -------------------------- |
| `python`, `py`   | `.py`     | pytest                     |
| `javascript`, `js` | `.js`   | Jest                       |
| `typescript`, `ts` | `.ts`   | Jest + ts-jest             |
| `go`, `golang`   | `.go`     | go test                    |
| `java`           | `.java`   | JUnit 5                    |
| `ruby`, `rb`     | `.rb`     | RSpec                      |
| `php`            | `.php`    | PHPUnit                    |
| `csharp`, `cs`   | `.cs`     | xUnit                      |
| `cpp`, `c++`     | `.cpp`    | Google Test                |
| `rust`, `rs`     | `.rs`     | cargo test                 |
| `kotlin`, `kt`   | `.kt`     | JUnit 5 + Kotlin           |
| `swift`          | `.swift`  | XCTest                     |

---

## How It Works

```
qalix analyze app.js
        │
        ▼
1. Read the file from disk
        │
        ▼
2. Detect language (.js → JavaScript / Jest)
        │
        ▼
3. POST /api/v1/jobs
   { filename: "app.js", code: "..." }
        │
        ▼
4. Receive { job_id: 42 }
        │
        ▼
5. Poll GET /api/v1/jobs/42 every 2 seconds
   pending → running → completed
        │
        ▼
6. Print generated test code
   (optionally save to --output)
```

---

## Project Structure

```
cli/
├── bin/
│   └── qalix.js              # Entry point — defines the "qalix" command
├── src/
│   ├── commands/
│   │   └── analyze.js        # Full analyze command logic
│   ├── api/
│   │   └── client.js         # createJob() and pollJob() — HTTP calls to backend
│   └── utils/
│       └── language.js       # Language detection by extension or --lang flag
├── package.json
└── README.md
```
