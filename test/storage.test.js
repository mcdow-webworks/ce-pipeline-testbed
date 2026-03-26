import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, existsSync } from 'node:fs';
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
