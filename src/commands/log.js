import { loadLog, saveLog } from '../storage.js';

function printLogUsage() {
  console.log('Usage: bookshelf log <subcommand>');
  console.log('');
  console.log('Subcommands:');
  console.log('  start <title>              Start reading a book');
  console.log('  finish <title>             Finish reading a book');
  console.log('  list                       Show all books');
  console.log('');
  console.log('Options:');
  console.log('  --rating <1-5>             Rate a book (finish only)');
  console.log('  --date <YYYY-MM-DD>        Override date');
}

function todayString() {
  const d = new Date();
  return d.getFullYear() + '-' +
    String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0');
}

function parseDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const d = new Date(value + 'T00:00:00');
  if (isNaN(d.getTime())) return null;
  const [y, m, day] = value.split('-').map(Number);
  if (d.getFullYear() !== y || d.getMonth() + 1 !== m || d.getDate() !== day) return null;
  return value;
}

function parseRating(value) {
  const n = Number(value);
  if (!Number.isInteger(n) || n < 1 || n > 5) return null;
  return n;
}

function findEntry(entries, title, status) {
  return entries.findIndex(
    e => e.title.toLowerCase() === title.toLowerCase() && e.status === status
  );
}

function extractDate(args) {
  const dateIdx = args.indexOf('--date');
  if (dateIdx === -1) return todayString();
  const dateValue = args[dateIdx + 1];
  const parsed = parseDate(dateValue);
  if (!parsed) {
    console.error(`Error: Invalid date "${dateValue}". Use YYYY-MM-DD format.`);
    process.exit(1);
  }
  return parsed;
}

function handleStart(args, entries) {
  const title = args[0];
  if (!title) {
    console.error('Error: Missing book title.');
    console.error('Usage: bookshelf log start "<title>" [--date YYYY-MM-DD]');
    process.exit(1);
  }

  const date = extractDate(args);

  const readingIdx = findEntry(entries, title, 'reading');
  if (readingIdx !== -1) {
    console.error(`Error: "${entries[readingIdx].title}" is already in progress.`);
    process.exit(1);
  }

  entries.push({
    title,
    startDate: date,
    finishDate: null,
    rating: null,
    status: 'reading'
  });

  saveLog(entries);
  console.log(`Started reading "${title}" (${date})`);
}

function handleFinish(args, entries) {
  const title = args[0];
  if (!title) {
    console.error('Error: Missing book title.');
    console.error('Usage: bookshelf log finish "<title>" [--rating 1-5] [--date YYYY-MM-DD]');
    process.exit(1);
  }

  const date = extractDate(args);

  let rating = null;
  const ratingIdx = args.indexOf('--rating');
  if (ratingIdx !== -1) {
    const ratingValue = args[ratingIdx + 1];
    const parsed = parseRating(ratingValue);
    if (parsed === null) {
      console.error(`Error: Invalid rating "${ratingValue}". Must be an integer from 1 to 5.`);
      process.exit(1);
    }
    rating = parsed;
  }

  const readingIdx = findEntry(entries, title, 'reading');
  if (readingIdx !== -1) {
    entries[readingIdx].finishDate = date;
    entries[readingIdx].rating = rating;
    entries[readingIdx].status = 'finished';
  } else {
    // Auto-backfill: create entry with start date = finish date
    entries.push({
      title,
      startDate: date,
      finishDate: date,
      rating,
      status: 'finished'
    });
  }

  saveLog(entries);
  const ratingStr = rating ? ` — ${rating}/5` : '';
  console.log(`Finished "${title}" (${date})${ratingStr}`);
}

function handleList() {
  const entries = loadLog();

  if (entries.length === 0) {
    console.log('No books logged yet.');
    return;
  }

  const headers = ['Title', 'Status', 'Started', 'Finished', 'Rating'];
  const rows = entries.map(e => [
    e.title,
    e.status,
    e.startDate || '—',
    e.finishDate || '—',
    e.rating ? `${e.rating}/5` : '—'
  ]);

  const widths = headers.map((h, i) =>
    Math.max(h.length, ...rows.map(r => r[i].length))
  );

  const header = headers.map((h, i) => h.padEnd(widths[i])).join('  ');
  const separator = widths.map(w => '—'.repeat(w)).join('  ');

  console.log(header);
  console.log(separator);
  for (const row of rows) {
    console.log(row.map((cell, i) => cell.padEnd(widths[i])).join('  '));
  }
}

export function handleLog(args) {
  const subcommand = args[0];

  if (subcommand === 'start') {
    const entries = loadLog();
    handleStart(args.slice(1), entries);
  } else if (subcommand === 'finish') {
    const entries = loadLog();
    handleFinish(args.slice(1), entries);
  } else if (subcommand === 'list') {
    handleList();
  } else {
    printLogUsage();
    process.exit(subcommand ? 1 : 0);
  }
}
