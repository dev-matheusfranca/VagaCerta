import { authorization } from './auth'

export interface WorkingHours {
  weekday: number
  start: string
  end: string
}

export interface Professional {
  id: string
  name: string
  specialty: string
  working_hours: WorkingHours[]
}

export interface Service {
  id: string
  name: string
  duration_minutes: number
  price_cents: number
}

export interface Business {
  id: string
  name: string
  category: string
  description: string
  address: string
  timezone: string
}

export interface BusinessDetail extends Business {
  professionals: Professional[]
  services: Service[]
}

export interface Booking {
  id: string
  business_id: string
  professional_id: string
  service_id: string
  starts_at: string
  ends_at: string
  customer_name: string
  customer_email: string
  status: 'confirmed' | 'cancelled' | 'held' | 'released'
}

export type NewBooking = Omit<Booking, 'id' | 'ends_at' | 'status'>

export interface DayStats {
  day: string
  bookings: number
  cancellations: number
  revenue_cents: number
  offers: number
  offers_claimed: number
  offers_expired: number
  recovered_revenue_cents: number
}

export interface WaitlistEntryIn {
  business_id: string
  professional_id: string
  service_id: string
  day: string
  customer_name: string
  customer_email: string
}

export interface Offer {
  id: string
  booking_id: string
  status: 'pending' | 'claimed' | 'expired'
  starts_at: string
  ends_at: string
  expires_at: string
  entry: {
    customer_name: string
    details: {
      business_name: string
      business_address: string
      timezone: string
      professional_name: string
      service_name: string
      price_cents: number
    }
  }
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'tool'
  content: string
  tool_calls?: { function: { name: string; arguments: Record<string, unknown> } }[]
  tool_name?: string
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const body = await response.json()
  if (!response.ok) {
    const message = typeof body.detail === 'string' ? body.detail : 'Verifique os dados informados'
    throw new ApiError(response.status, message)
  }
  return body
}

export const api = {
  businesses: () => request<Business[]>('/api/catalog/businesses'),
  business: (id: string) => request<BusinessDetail>(`/api/catalog/businesses/${id}`),
  availability: (params: Record<string, string>) =>
    request<{ slots: string[] }>(`/api/booking/availability?${new URLSearchParams(params)}`),
  createBooking: (data: NewBooking) =>
    request<Booking>('/api/booking/bookings', { method: 'POST', body: JSON.stringify(data) }),
  booking: (id: string) => request<Booking>(`/api/booking/bookings/${id}`),
  cancelBooking: (id: string) =>
    request<Booking>(`/api/booking/bookings/${id}/cancel`, { method: 'POST' }),
  joinWaitlist: (data: WaitlistEntryIn) =>
    request<{ id: string; position: number }>('/api/waitlist/entries', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  offer: (id: string) => request<Offer>(`/api/waitlist/offers/${id}`),
  agenda: async (businessId: string, date: string) =>
    request<Booking[]>(`/api/booking/businesses/${businessId}/agenda?date=${date}`, {
      headers: await authorization(),
    }),
  stats: async (businessId: string, from: string, to: string) =>
    request<DayStats[]>(`/api/analytics/businesses/${businessId}/stats?from=${from}&to=${to}`, {
      headers: await authorization(),
    }),
  claimOffer: (id: string) =>
    request<Offer>(`/api/waitlist/offers/${id}/claim`, { method: 'POST' }),
  chat: (messages: ChatMessage[]) =>
    request<{ messages: ChatMessage[] }>('/api/assistant/chat', {
      method: 'POST',
      body: JSON.stringify({ messages }),
    }),
}
