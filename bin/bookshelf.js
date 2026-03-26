#!/usr/bin/env node

import { handleLog } from '../src/commands/log.js';

const args = process.argv.slice(2);
const command = args[0];

if (command === 'log') {
  handleLog(args.slice(1));
} else {
  console.log('Usage: bookshelf <command>');
  console.log('');
  console.log('Commands:');
  console.log('  log start <title>   Start reading a book');
  console.log('  log finish <title>  Finish reading a book');
  console.log('  log list            Show all books');
  process.exit(command ? 1 : 0);
}
