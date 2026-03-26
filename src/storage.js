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
  return JSON.parse(data);
}

export function saveLog(entries) {
  const filePath = getLogPath();
  const dir = dirname(filePath);
  mkdirSync(dir, { recursive: true });
  writeFileSync(filePath, JSON.stringify(entries, null, 2) + '\n', 'utf-8');
}
