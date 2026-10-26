import test from 'node:test';
import assert from 'node:assert/strict';
import { parseDocumentListResponse, calculateDocumentStats } from './documents.js';

test('parseDocumentListResponse - standard FastAPI response with items and total', () => {
  const apiResponse = {
    items: [
      {
        id: 'f45bfe7f-747f-45c8-8afd-d1f8243c5ddb',
        title: 'Northstar demo employee leave policy',
        filename: 'northstar_demo_employee_leave_policy.pdf',
        file_size_bytes: 3734,
        content_type: 'application/pdf',
        status: 'completed',
        total_chunks: 6,
        error_message: null,
        created_at: '2026-10-26T09:15:08.658287Z',
        updated_at: '2026-10-26T09:15:08.735271Z',
      },
    ],
    total: 1,
  };

  const parsed = parseDocumentListResponse(apiResponse);

  assert.strictEqual(parsed.items.length, 1);
  assert.strictEqual(parsed.total, 1);
  assert.strictEqual(parsed.items[0].id, 'f45bfe7f-747f-45c8-8afd-d1f8243c5ddb');
  assert.strictEqual(parsed.items[0].title, 'Northstar demo employee leave policy');
  assert.strictEqual(parsed.items[0].status, 'completed');
  assert.strictEqual(parsed.items[0].total_chunks, 6);
});

test('parseDocumentListResponse - plain array fallback', () => {
  const arrayResponse = [
    {
      id: 'doc-1',
      title: 'IT Policy',
      status: 'completed',
      total_chunks: 4,
    },
    {
      id: 'doc-2',
      title: 'Security Policy',
      status: 'queued',
      total_chunks: 0,
    },
  ];

  const parsed = parseDocumentListResponse(arrayResponse);

  assert.strictEqual(parsed.items.length, 2);
  assert.strictEqual(parsed.total, 2);
  assert.strictEqual(parsed.items[0].title, 'IT Policy');
});

test('parseDocumentListResponse - legacy documents property fallback', () => {
  const legacyResponse = {
    documents: [
      {
        id: 'doc-legacy',
        title: 'Legacy Policy',
        status: 'completed',
        total_chunks: 2,
      },
    ],
    total: 1,
  };

  const parsed = parseDocumentListResponse(legacyResponse);

  assert.strictEqual(parsed.items.length, 1);
  assert.strictEqual(parsed.total, 1);
  assert.strictEqual(parsed.items[0].title, 'Legacy Policy');
});

test('parseDocumentListResponse - null, undefined, or empty object handling', () => {
  assert.deepStrictEqual(parseDocumentListResponse(null), { items: [], total: 0 });
  assert.deepStrictEqual(parseDocumentListResponse(undefined), { items: [], total: 0 });
  assert.deepStrictEqual(parseDocumentListResponse({}), { items: [], total: 0 });
  assert.deepStrictEqual(parseDocumentListResponse({ items: [], total: 0 }), { items: [], total: 0 });
});

test('calculateDocumentStats - Northstar demo employee leave policy', () => {
  const northstarDocs = [
    {
      id: 'f45bfe7f-747f-45c8-8afd-d1f8243c5ddb',
      title: 'Northstar demo employee leave policy',
      status: 'completed',
      total_chunks: 6,
    },
  ];

  const stats = calculateDocumentStats(northstarDocs, 1);

  assert.strictEqual(stats.total, 1, 'Total documents must be 1');
  assert.strictEqual(stats.completed, 1, 'Completed and indexed documents must be 1');
  assert.strictEqual(stats.processing, 0, 'In processing/queue must be 0');
  assert.strictEqual(stats.failed, 0, 'Failed ingestions must be 0');
});

test('calculateDocumentStats - multiple mixed document statuses', () => {
  const mixedDocs = [
    { id: '1', status: 'completed' },
    { id: '2', status: 'completed' },
    { id: '3', status: 'processing' },
    { id: '4', status: 'queued' },
    { id: '5', status: 'pending' },
    { id: '6', status: 'failed' },
  ];

  const stats = calculateDocumentStats(mixedDocs);

  assert.strictEqual(stats.total, 6);
  assert.strictEqual(stats.completed, 2);
  assert.strictEqual(stats.processing, 3); // processing + queued + pending
  assert.strictEqual(stats.failed, 1);
});

test('calculateDocumentStats - paginated subset uses serverTotal', () => {
  const firstPageDocs = [
    { id: '1', status: 'completed' },
    { id: '2', status: 'completed' },
  ];

  const stats = calculateDocumentStats(firstPageDocs, 25);

  assert.strictEqual(stats.total, 25, 'Should use serverTotal when provided');
  assert.strictEqual(stats.completed, 2);
});

test('calculateDocumentStats - empty or invalid documents array', () => {
  assert.deepStrictEqual(calculateDocumentStats([]), {
    total: 0,
    completed: 0,
    processing: 0,
    failed: 0,
  });

  assert.deepStrictEqual(calculateDocumentStats(null), {
    total: 0,
    completed: 0,
    processing: 0,
    failed: 0,
  });
});
