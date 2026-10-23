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
  status: 'confirmed' | 'cancelled'
}

export type NewBooking = Omit<Booking, 'id' | 'ends_at' | 'status'>

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, headers: { 'Content-Type': 'application/json' } })
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
}
