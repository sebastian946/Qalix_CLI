#!/usr/bin/env node
import { program } from 'commander'
import { analyzeCommand } from '../src/commands/analyze.js'

program
  .name('qalix')
  .description('AI-powered test generation CLI — Qalix')
  .version('1.0.0')

program
  .command('analyze <file>')
  .description('Analyze a file and generate test scenarios using AI')
  .option(
    '-l, --lang <language>',
    'Programming language (e.g. python, javascript, typescript, go, java, ruby, rust...)'
  )
  .option(
    '-u, --url <url>',
    'Qalix backend URL',
    'http://localhost:8000'
  )
  .option(
    '-o, --output <file>',
    'Save generated tests to a file'
  )
  .action(analyzeCommand)

program.parse()
