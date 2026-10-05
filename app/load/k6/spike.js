// Spike test: ramps the arrival rate from a baseline up to ~100 rps and back.
// Usage: k6 run -e BASE_URL=http://localhost:8000 load/k6/spike.js
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = (__ENV.BASE_URL || 'http://orders-api:8000').replace(/\/$/, '');
const PEAK_RPS = parseInt(__ENV.PEAK_RPS || '100', 10);

const QUERIES = ['pierogi', 'zupa', 'schabowy', 'rosół', 'żurek', 'sałatka', 'makaron', 'kurczak'];

export const options = {
  scenarios: {
    spike: {
      executor: 'ramping-arrival-rate',
      startRate: 5,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 400,
      stages: [
        { target: 10, duration: '1m' },
        { target: PEAK_RPS, duration: '30s' },
        { target: PEAK_RPS, duration: '3m' },
        { target: 10, duration: '30s' },
        { target: 10, duration: '1m' },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    'http_req_duration{endpoint:menu}': ['p(95)<500'],
    'http_req_duration{endpoint:search}': ['p(95)<800'],
  },
};

export default function () {
  if (Math.random() < 0.75) {
    const res = http.get(`${BASE_URL}/api/menu`, { tags: { endpoint: 'menu' } });
    check(res, { 'menu 200': (r) => r.status === 200 });
  } else {
    const q = QUERIES[Math.floor(Math.random() * QUERIES.length)];
    const res = http.get(`${BASE_URL}/api/menu/search?q=${encodeURIComponent(q)}`, {
      tags: { endpoint: 'search' },
    });
    check(res, { 'search 200': (r) => r.status === 200 });
  }
}
