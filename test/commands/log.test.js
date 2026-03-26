import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { setLogPath, loadLog, saveLog } from '../../src/storage.js';
import { handleLog } from '../../src/commands/log.js';

// Helper to capture console output and prevent process.exit
function runCommand(args) {
  const output = { stdout: [], stderr: [], exitCode: null };
  const origLog = console.log;
  const origErr = console.error;
  const origExit = process.exit;

  console.log = (...a) => output.stdout.push(a.join(' '));
  console.error = (...a) => output.stderr.push(a.join(' '));
  process.exit = (code) => {
    output.exitCode = code;
    throw new Error('__EXIT__');
  };

  try {
    handleLog(args);
  } catch (e) {
    if (e.message !== '__EXIT__') throw e;
  } finally {
    console.log = origLog;
    console.error = origErr;
    process.exit = origExit;
  }
  return output;
}

describe('log start', () => {
  let tempDir;

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), 'bookshelf-test-'));
    setLogPath(join(tempDir, 'reading-log.json'));
  });

  afterEach(() => {
    rmSync(tempDir, { recursive: true, force: true });
    setLogPath(null);
  });

  it('creates entry with status reading and today\'s date', () => {
    const out = runCommand(['start', 'The Pragmatic Programmer']);
    assert.equal(out.exitCode, null);
    assert.ok(out.stdout[0].includes('Started reading'));
    const entries = loadLog();
    assert.equal(entries.length, 1);
    assert.equal(entries[0].title, 'The Pragmatic Programmer');
    assert.equal(entries[0].status, 'reading');
    assert.equal(entries[0].finishDate, null);
    assert.equal(entries[0].rating, null);
  });

  it('rejects starting a book already in reading status', () => {
    runCommand(['start', 'The Pragmatic Programmer']);
    const out = runCommand(['start', 'The Pragmatic Programmer']);
    assert.equal(out.exitCode, 1);
    assert.ok(out.stderr[0].includes('already in progress'));
  });

  it('allows starting a finished book (re-read creates new entry)', () => {
    saveLog([{
      title: 'The Pragmatic Programmer',
      startDate: '2026-01-01',
      finishDate: '2026-01-15',
      rating: 4,
      status: 'finished'
    }]);
    const out = runCommand(['start', 'The Pragmatic Programmer']);
    assert.equal(out.exitCode, null);
    const entries = loadLog();
    assert.equal(entries.length, 2);
    assert.equal(entries[0].status, 'finished');
    assert.equal(entries[1].status, 'reading');
  });

  it('uses --date override instead of today', () => {
    runCommand(['start', 'DDIA', '--date', '2026-01-15']);
    const entries = loadLog();
    assert.equal(entries[0].startDate, '2026-01-15');
  });

  it('rejects invalid --date format', () => {
    const out = runCommand(['start', 'DDIA', '--date', 'not-a-date']);
    assert.equal(out.exitCode, 1);
    assert.ok(out.stderr[0].includes('Invalid date'));
  });

  it('title matching is case-insensitive', () => {
    runCommand(['start', 'The Pragmatic Programmer']);
    const out = runCommand(['start', 'the pragmatic programmer']);
    assert.equal(out.exitCode, 1);
    assert.ok(out.stderr[0].includes('already in progress'));
  });

  it('errors when title is missing', () => {
    const out = runCommand(['start']);
    assert.equal(out.exitCode, 1);
    assert.ok(out.stderr[0].includes('Missing book title'));
  });
});

describe('log finish', () => {
  let tempDir;

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), 'bookshelf-test-'));
    setLogPath(join(tempDir, 'reading-log.json'));
  });

  afterEach(() => {
    rmSync(tempDir, { recursive: true, force: true });
    setLogPath(null);
  });

  it('finishes a reading book and sets status to finished', () => {
    runCommand(['start', 'DDIA']);
    const out = runCommand(['finish', 'DDIA']);
    assert.equal(out.exitCode, null);
    const entries = loadLog();
    assert.equal(entries[0].status, 'finished');
    assert.ok(entries[0].finishDate);
  });

  it('stores rating when provided', () => {
    runCommand(['start', 'DDIA']);
    runCommand(['finish', 'DDIA', '--rating', '5']);
    const entries = loadLog();
    assert.equal(entries[0].rating, 5);
  });

  it('rejects invalid ratings: 0', () => {
    runCommand(['start', 'DDIA']);
    const out = runCommand(['finish', 'DDIA', '--rating', '0']);
    assert.equal(out.exitCode, 1);
    assert.ok(out.stderr[0].includes('Invalid rating'));
  });

  it('rejects invalid ratings: 6', () => {
    runCommand(['start', 'DDIA']);
    const out = runCommand(['finish', 'DDIA', '--rating', '6']);
    assert.equal(out.exitCode, 1);
    assert.ok(out.stderr[0].includes('Invalid rating'));
  });

  it('rejects invalid ratings: 3.5', () => {
    runCommand(['start', 'DDIA']);
    const out = runCommand(['finish', 'DDIA', '--rating', '3.5']);
    assert.equal(out.exitCode, 1);
    assert.ok(out.stderr[0].includes('Invalid rating'));
  });

  it('rejects invalid ratings: abc', () => {
    runCommand(['start', 'DDIA']);
    const out = runCommand(['finish', 'DDIA', '--rating', 'abc']);
    assert.equal(out.exitCode, 1);
    assert.ok(out.stderr[0].includes('Invalid rating'));
  });

  it('auto-backfills start date when finishing unstarted book', () => {
    const out = runCommand(['finish', 'New Book', '--date', '2026-03-20']);
    assert.equal(out.exitCode, null);
    const entries = loadLog();
    assert.equal(entries[0].startDate, '2026-03-20');
    assert.equal(entries[0].finishDate, '2026-03-20');
    assert.equal(entries[0].status, 'finished');
  });

  it('uses --date override for finish date', () => {
    runCommand(['start', 'DDIA']);
    runCommand(['finish', 'DDIA', '--date', '2026-01-20']);
    const entries = loadLog();
    assert.equal(entries[0].finishDate, '2026-01-20');
  });

  it('title matching is case-insensitive on finish', () => {
    runCommand(['start', 'The Pragmatic Programmer']);
    const out = runCommand(['finish', 'the pragmatic programmer', '--rating', '5']);
    assert.equal(out.exitCode, null);
    const entries = loadLog();
    assert.equal(entries[0].status, 'finished');
    assert.equal(entries[0].rating, 5);
  });

  it('rejects invalid --date format on finish', () => {
    runCommand(['start', 'DDIA']);
    const out = runCommand(['finish', 'DDIA', '--date', 'not-a-date']);
    assert.equal(out.exitCode, 1);
    assert.ok(out.stderr[0].includes('Invalid date'));
  });

  it('rejects invalid calendar date like 2026-02-30', () => {
    runCommand(['start', 'DDIA']);
    const out = runCommand(['finish', 'DDIA', '--date', '2026-02-30']);
    assert.equal(out.exitCode, 1);
    assert.ok(out.stderr[0].includes('Invalid date'));
  });

  it('errors when title is missing', () => {
    const out = runCommand(['finish']);
    assert.equal(out.exitCode, 1);
    assert.ok(out.stderr[0].includes('Missing book title'));
  });
});

describe('log list', () => {
  let tempDir;

  beforeEach(() => {
    tempDir = mkdtempSync(join(tmpdir(), 'bookshelf-test-'));
    setLogPath(join(tempDir, 'reading-log.json'));
  });

  afterEach(() => {
    rmSync(tempDir, { recursive: true, force: true });
    setLogPath(null);
  });

  it('prints friendly message when log is empty', () => {
    const out = runCommand(['list']);
    assert.ok(out.stdout[0].includes('No books logged yet'));
  });

  it('displays mix of reading and finished books', () => {
    saveLog([
      { title: 'Book A', startDate: '2026-01-01', finishDate: '2026-01-15', rating: 4, status: 'finished' },
      { title: 'Book B', startDate: '2026-02-01', finishDate: null, rating: null, status: 'reading' }
    ]);
    const out = runCommand(['list']);
    // Header + separator + 2 data rows = 4 lines
    assert.equal(out.stdout.length, 4);
    assert.ok(out.stdout[0].includes('Title'));
    assert.ok(out.stdout[2].includes('Book A'));
    assert.ok(out.stdout[2].includes('4/5'));
    assert.ok(out.stdout[3].includes('Book B'));
    assert.ok(out.stdout[3].includes('reading'));
  });

  it('shows placeholder for missing rating and finish date', () => {
    saveLog([
      { title: 'Book C', startDate: '2026-03-01', finishDate: null, rating: null, status: 'reading' }
    ]);
    const out = runCommand(['list']);
    const dataRow = out.stdout[2];
    // Should have dash placeholders for finishDate and rating
    assert.ok(dataRow.includes('—'));
  });
});

describe('log usage', () => {
  it('prints usage when no subcommand given', () => {
    const out = runCommand([]);
    assert.equal(out.exitCode, 0);
    assert.ok(out.stdout[0].includes('Usage'));
  });

  it('exits with error on unknown subcommand', () => {
    const out = runCommand(['unknown']);
    assert.equal(out.exitCode, 1);
  });
});
