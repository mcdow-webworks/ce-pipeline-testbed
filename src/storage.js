import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';

let logPathOverride = null;

export function setLogPath(path) {
  logPathOverride = path;
}

export function getLogPath() {
  if (logPathOverride) return logPathOverride;
  return join(homedir(), '.bookshelf', 'reading-log.json');
}

export function loadLog() {
  const filePath = getLogPath();
  if (!existsSync(filePath)) return [];
  const data = readFileSync(filePath, 'utf-8');
  let parsed;
  try {
    parsed = JSON.parse(data);
  } catch {
    console.error(`Error: Reading log file is corrupted: ${filePath}`);
    console.error('Fix the file manually or delete it to start fresh.');
    process.exit(1);
  }
  if (!Array.isArray(parsed)) {
    console.error(`Error: Reading log file has unexpected format: ${filePath}`);
    console.error('Expected a JSON array. Fix the file manually or delete it to start fresh.');
    process.exit(1);
  }
  return parsed;
}

export function saveLog(entries) {
  const filePath = getLogPath();
  const dir = dirname(filePath);
  mkdirSync(dir, { recursive: true });
  writeFileSync(filePath, JSON.stringify(entries, null, 2) + '\n', 'utf-8');
}
