// Teste de carga pelo gateway: muita gente consultando horários e 50 pessoas disputando o
// mesmo horário ao mesmo tempo. Só uma pode conseguir; as outras recebem 409 ou 429.
import http from 'k6/http'
import { check } from 'k6'
import { Counter } from 'k6/metrics'

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080'
const bookingsCreated = new Counter('bookings_created')

export const options = {
  scenarios: {
    availability: { executor: 'constant-vus', vus: 20, duration: '20s', exec: 'browse' },
    race: {
      executor: 'shared-iterations',
      vus: 50,
      iterations: 50,
      startTime: '5s',
      exec: 'race',
    },
  },
  thresholds: {
    'http_req_duration{scenario:availability}': ['p(95)<500'],
    'http_req_failed{scenario:availability}': ['rate==0'],
    bookings_created: ['count==1'],
    checks: ['rate==1'],
  },
}

const query = (params) =>
  Object.entries(params)
    .map(([key, value]) => `${key}=${encodeURIComponent(value)}`)
    .join('&')

export function setup() {
  const business = http
    .get(`${BASE_URL}/api/catalog/businesses`)
    .json()
    .find((b) => b.name.includes('Navalha'))
  const detail = http.get(`${BASE_URL}/api/catalog/businesses/${business.id}`).json()
  const choice = {
    business_id: business.id,
    professional_id: detail.professionals[0].id,
    service_id: detail.services[0].id,
  }
  for (let offset = 1; offset < 15; offset++) {
    const date = new Date(Date.now() + offset * 86_400_000).toISOString().slice(0, 10)
    const { slots } = http.get(`${BASE_URL}/api/booking/availability?${query({ ...choice, date })}`).json()
    if (slots.length) return { choice, date, slot: slots[slots.length - 1] }
  }
  throw new Error('Nenhum horário livre nas próximas duas semanas')
}

export function browse({ choice, date }) {
  const response = http.get(`${BASE_URL}/api/booking/availability?${query({ ...choice, date })}`, {
    tags: { name: 'GET /availability' },
  })
  check(response, { 'disponibilidade respondeu 200': (r) => r.status === 200 })
}

export function race({ choice, slot }) {
  const response = http.post(
    `${BASE_URL}/api/booking/bookings`,
    JSON.stringify({
      ...choice,
      starts_at: slot,
      customer_name: `Cliente ${__VU}`,
      customer_email: `cliente${__VU}@example.com`,
    }),
    { headers: { 'Content-Type': 'application/json' }, tags: { name: 'POST /bookings' } },
  )
  if (response.status === 201) bookingsCreated.add(1)
  check(response, {
    'reservou, perdeu a disputa (409) ou foi limitado (429)': (r) => [201, 409, 429].includes(r.status),
  })
}
