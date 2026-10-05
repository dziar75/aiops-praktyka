// Steady load: constant arrival rate mixing menu reads and order creation.
// Usage: k6 run -e BASE_URL=http://localhost:8000 -e RATE=20 -e DURATION=10m load/k6/steady.js
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = (__ENV.BASE_URL || 'http://orders-api:8000').replace(/\/$/, '');
const RATE = parseInt(__ENV.RATE || '20', 10);
const DURATION = __ENV.DURATION || '10m';

const JSON_HEADERS = { 'Content-Type': 'application/json' };

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',
      rate: RATE,
      timeUnit: '1s',
      duration: DURATION,
      preAllocatedVUs: 20,
      maxVUs: 100,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.02'],
    'http_req_duration{endpoint:menu}': ['p(95)<300'],
    'http_req_duration{endpoint:orders_create}': ['p(95)<1000'],
  },
};

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export default function () {
  const r = Math.random();
  if (r < 0.7) {
    const res = http.get(`${BASE_URL}/api/menu`, { tags: { endpoint: 'menu' } });
    check(res, { 'menu 200': (x) => x.status === 200 });
    return;
  }

  const items = [];
  const count = randInt(1, 3);
  for (let i = 0; i < count; i++) {
    items.push({ menu_item_id: randInt(1, 20), qty: randInt(1, 3) });
  }
  const payload = JSON.stringify({ employee_id: `e-${randInt(1, 500)}`, items });
  const res = http.post(`${BASE_URL}/api/orders`, payload, {
    headers: JSON_HEADERS,
    tags: { endpoint: 'orders_create' },
  });
  check(res, { 'order accepted': (x) => x.status >= 200 && x.status < 300 });
}
