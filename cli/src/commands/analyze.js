import fs from 'fs'
import path from 'path'
import chalk from 'chalk'
import ora from 'ora'
import { resolveLanguage } from '../utils/language.js'
import { createJob, pollJob } from '../api/client.js'

export async function analyzeCommand(file, options) {
  const spinner = ora({ color: 'cyan' })

  try {
    // ── 1. Validate file exists ──────────────────────────────────────────────
    const absolutePath = path.resolve(file)
    if (!fs.existsSync(absolutePath)) {
      console.error(chalk.red(`✗ File not found: ${absolutePath}`))
      process.exit(1)
    }

    // ── 2. Detect language ───────────────────────────────────────────────────
    const lang = resolveLanguage(path.basename(absolutePath), options.lang)

    const langLabel = lang.framework
      ? `${lang.name} → ${chalk.yellow(lang.framework)}`
      : lang.name

    console.log(chalk.cyan(`▸ Language: ${langLabel}`))

    if (lang.backendFilename !== path.basename(absolutePath)) {
      console.log(chalk.gray(`  (sending as "${lang.backendFilename}" to the backend)`))
    }

    // ── 3. Read file ─────────────────────────────────────────────────────────
    const code = fs.readFileSync(absolutePath, 'utf-8')

    if (code.trim().length === 0) {
      console.error(chalk.red('✗ File is empty.'))
      process.exit(1)
    }

    // ── 4. Create job ────────────────────────────────────────────────────────
    spinner.start('Sending code to the agent...')
    const { job_id } = await createJob(lang.backendFilename, code, options.url)
    spinner.succeed(`Job created ${chalk.gray(`(ID: ${job_id})`)}`)

    // ── 5. Poll until complete ───────────────────────────────────────────────
    spinner.start('Analyzing code...')

    const result = await pollJob(job_id, options.url, {
      intervalMs: 2000,
      onStatusChange: (status) => {
        if (status === 'running') spinner.text = 'Agent is generating tests...'
      },
    })

    spinner.succeed(chalk.green('Tests generated!'))

    // ── 6. Display result ────────────────────────────────────────────────────
    const separator = chalk.gray('─'.repeat(60))
    console.log(`\n${separator}`)
    console.log(chalk.bold(`  ${lang.name} tests — ${lang.framework ?? ''}`))
    console.log(`${separator}\n`)
    console.log(result)

    // ── 7. Save to file (optional) ───────────────────────────────────────────
    if (options.output) {
      fs.writeFileSync(options.output, result, 'utf-8')
      console.log(`\n${chalk.green('✓')} Saved to: ${chalk.underline(options.output)}`)
    }

  } catch (err) {
    spinner.fail(chalk.red(`Error: ${err.message}`))
    process.exit(1)
  }
}
