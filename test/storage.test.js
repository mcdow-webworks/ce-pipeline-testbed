import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { setLogPath, getLogPath, loadLog, saveLog } from '../src/storage.js';

describe('storage', () => {
  let tempDir;
  let tempFile;

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), 'bookshelf-test-'));
    tempFile = join(tempDir, 'reading-log.json');
    setLogPath(tempFile);
  });

  afterEach(() => {
    rmSync(tempDir, { recursive: true, force: true });
    setLogPath(null);
  });

  it('loadLog returns empty array when file does not exist', () => {
    const result = loadLog();
    assert.deepEqual(result, []);
  });

  it('saveLog creates directory and file when they do not exist', () => {
    const nested = join(tempDir, 'sub', 'reading-log.json');
    setLogPath(nested);
    saveLog([{ title: 'Test' }]);
    assert.ok(existsSync(nested));
  });

  it('loadLog returns parsed entries from existing file', () => {
    const entries = [{ title: 'Book A', status: 'reading' }];
    saveLog(entries);
    const result = loadLog();
    assert.deepEqual(result, entries);
  });

  it('saveLog overwrites existing file with updated entries', () => {
    saveLog([{ title: 'Old' }]);
    saveLog([{ title: 'New' }]);
    const result = loadLog();
    assert.equal(result.length, 1);
    assert.equal(result[0].title, 'New');
  });

  it('loadLog exits with error on corrupted JSON', () => {
    writeFileSync(tempFile, 'not valid json', 'utf-8');
    const origExit = process.exit;
    const origErr = console.error;
    let exitCode = null;
    const errors = [];
    process.exit = (code) => { exitCode = code; throw new Error('__EXIT__'); };
    console.error = (...a) => errors.push(a.join(' '));
    try {
      loadLog();
    } catch (e) {
      if (e.message !== '__EXIT__') throw e;
    } finally {
      process.exit = origExit;
      console.error = origErr;
    }
    assert.equal(exitCode, 1);
    assert.ok(errors[0].includes('corrupted'));
  });

  it('loadLog exits with error on non-array JSON', () => {
    writeFileSync(tempFile, '{"not": "an array"}', 'utf-8');
    const origExit = process.exit;
    const origErr = console.error;
    let exitCode = null;
    const errors = [];
    process.exit = (code) => { exitCode = code; throw new Error('__EXIT__'); };
    console.error = (...a) => errors.push(a.join(' '));
    try {
      loadLog();
    } catch (e) {
      if (e.message !== '__EXIT__') throw e;
    } finally {
      process.exit = origExit;
      console.error = origErr;
    }
    assert.equal(exitCode, 1);
    assert.ok(errors[0].includes('unexpected format'));
  });

  it('round-trip: save then load returns identical data', () => {
    const entries = [
      { title: 'The Pragmatic Programmer', startDate: '2026-03-20', finishDate: '2026-03-25', rating: 5, status: 'finished' },
      { title: 'DDIA', startDate: '2026-03-25', finishDate: null, rating: null, status: 'reading' }
    ];
    saveLog(entries);
    const result = loadLog();
    assert.deepEqual(result, entries);
  });
});
