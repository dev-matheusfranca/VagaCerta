<script setup lang="ts">
import {
  Ban,
  BellRing,
  CalendarCheck,
  ChevronLeft,
  ChevronRight,
  LoaderCircle,
  LogOut,
  UserCheck,
  UserX,
  Wallet,
} from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { api, ApiError, type Booking, type BusinessDetail } from '../api'
import { keycloak } from '../auth'
import PastStats from '../components/PastStats.vue'
import UpcomingStats from '../components/UpcomingStats.vue'
import { category, currency, initials, longDate, time } from '../format'

const business = ref<BusinessDetail>()
const bookings = ref<Booking[]>()
const day = ref('')
const notLinked = ref(false)
const cancelling = ref('')
const recording = ref('')
const error = ref('')
const now = Date.now()

const ownerName = keycloak.tokenParsed?.given_name

function logout() {
  keycloak.logout({ redirectUri: `${location.origin}/` })
}

const services = computed(() => new Map(business.value?.services.map((s) => [s.id, s])))
const columns = computed(() =>
  business.value?.professionals.map((professional) => ({
    professional,
    bookings: bookings.value?.filter((b) => b.professional_id === professional.id) ?? [],
  })),
)
// Atendimentos já feitos continuam na agenda do dia, com o comparecimento registrado.
const confirmed = computed(
  () => bookings.value?.filter((b) => ['confirmed', 'completed', 'no_show'].includes(b.status)) ?? [],
)
const started = (booking: Booking) => new Date(booking.starts_at).getTime() <= now
const stats = computed(() => [
  { icon: CalendarCheck, label: 'Agendamentos', value: String(confirmed.value.length) },
  {
    icon: BellRing,
    label: 'Reservados para a fila',
    value: String(bookings.value?.filter((b) => b.status === 'held').length ?? 0),
  },
  {
    icon: Wallet,
    label: 'Receita prevista',
    value: currency(
      confirmed.value.reduce((sum, b) => sum + (services.value.get(b.service_id)?.price_cents ?? 0), 0),
    ),
  },
])

async function loadAgenda() {
  const requested = day.value
  bookings.value = undefined
  const agenda = await api.agenda(business.value!.id, requested)
  if (requested === day.value) bookings.value = agenda
}

function shiftDay(days: number) {
  const date = new Date(`${day.value}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  day.value = date.toISOString().slice(0, 10)
}

watch(day, loadAgenda)

onMounted(async () => {
  if (!keycloak.authenticated) return keycloak.login({ redirectUri: location.href })
  const [businessId] = keycloak.tokenParsed?.businesses ?? []
  if (!businessId) {
    notLinked.value = true
    return
  }
  business.value = await api.business(businessId)
  day.value = new Intl.DateTimeFormat('en-CA', { timeZone: business.value.timezone }).format(
    new Date(),
  )
})

async function record(booking: Booking, outcome: 'completed' | 'no_show') {
  recording.value = booking.id
  error.value = ''
  try {
    await api.recordOutcome(booking.id, outcome)
    await loadAgenda()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Não foi possível registrar'
  } finally {
    recording.value = ''
  }
}

async function cancel(booking: Booking) {
  if (!confirm(`Cancelar o horário de ${booking.customer_name}? A vaga vai para a lista de espera.`))
    return
  cancelling.value = booking.id
  error.value = ''
  try {
    await api.cancelBooking(booking.id)
    await loadAgenda()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Não foi possível cancelar'
  } finally {
    cancelling.value = ''
  }
}
</script>

<template>
  <div v-if="notLinked" class="mx-auto max-w-xl px-4 py-24 text-center sm:px-6">
    <p class="text-lg font-semibold">Seu usuário não está vinculado a nenhum estabelecimento.</p>
    <button class="mt-6 font-bold text-brand-700" @click="logout">Sair</button>
  </div>

  <div v-else-if="business">
    <section class="relative overflow-hidden bg-brand-950 text-white">
      <div
        class="pointer-events-none absolute -top-32 right-0 size-96 rounded-full bg-brand-500/25 blur-3xl"
      />
      <div
        class="relative mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6 px-4 pt-8 pb-24 sm:px-6"
      >
        <div class="flex items-center gap-5">
          <span
            :class="category(business.category).tone"
            class="grid size-14 shrink-0 place-items-center rounded-2xl bg-linear-to-br shadow-lg ring-4 ring-white/10"
          >
            <component :is="category(business.category).icon" class="size-7" />
          </span>
          <div>
            <p class="text-sm font-semibold text-amber-400">Painel do estabelecimento</p>
            <h1 class="text-2xl font-extrabold tracking-tight sm:text-3xl">{{ business.name }}</h1>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <span class="text-sm text-brand-100/70">Olá, {{ ownerName }}</span>
          <button
            class="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2 text-sm font-semibold transition hover:bg-white/20"
            @click="logout"
          >
            <LogOut class="size-4" /> Sair
          </button>
        </div>
      </div>
    </section>

    <div class="relative mx-auto -mt-14 max-w-6xl space-y-6 px-4 pb-16 sm:px-6">
      <div
        class="flex flex-wrap items-center justify-between gap-4 rounded-3xl bg-white p-4 shadow-sm ring-1 ring-ink/5 sm:px-6"
      >
        <div class="flex items-center gap-2">
          <button
            class="grid size-10 place-items-center rounded-xl bg-canvas transition hover:bg-brand-50"
            aria-label="Dia anterior"
            @click="shiftDay(-1)"
          >
            <ChevronLeft class="size-5" />
          </button>
          <input
            v-model="day"
            type="date"
            class="rounded-xl border border-ink/10 bg-canvas px-3 py-2 font-semibold outline-none focus:border-brand-500"
          />
          <button
            class="grid size-10 place-items-center rounded-xl bg-canvas transition hover:bg-brand-50"
            aria-label="Próximo dia"
            @click="shiftDay(1)"
          >
            <ChevronRight class="size-5" />
          </button>
        </div>
        <p v-if="day" class="font-bold first-letter:uppercase">
          {{ longDate(`${day}T12:00:00Z`, 'UTC') }}
        </p>
      </div>

      <div class="grid gap-4 sm:grid-cols-3">
        <div
          v-for="stat in stats"
          :key="stat.label"
          class="flex items-center gap-4 rounded-3xl bg-white p-5 shadow-sm ring-1 ring-ink/5"
        >
          <span class="grid size-12 place-items-center rounded-2xl bg-brand-50 text-brand-700">
            <component :is="stat.icon" class="size-6" />
          </span>
          <div>
            <p class="text-sm text-ink/50">{{ stat.label }}</p>
            <p class="text-2xl font-extrabold">{{ bookings ? stat.value : '—' }}</p>
          </div>
        </div>
      </div>

      <p v-if="error" class="rounded-2xl bg-rose-50 p-4 text-sm font-medium text-rose-700">
        {{ error }}
      </p>

      <div class="grid gap-6 lg:grid-cols-2">
        <section
          v-for="column in columns"
          :key="column.professional.id"
          class="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-ink/5"
        >
          <header class="flex items-center gap-3">
            <span
              class="grid size-11 place-items-center rounded-full bg-linear-to-br from-brand-400 to-brand-700 font-bold text-white"
            >
              {{ initials(column.professional.name) }}
            </span>
            <div class="flex-1">
              <h2 class="font-bold">{{ column.professional.name }}</h2>
              <p class="text-sm text-ink/50">{{ column.professional.specialty }}</p>
            </div>
            <span class="rounded-full bg-canvas px-3 py-1 text-sm font-bold text-ink/60">
              {{ column.bookings.length }}
            </span>
          </header>

          <div v-if="!bookings" class="mt-5 space-y-2">
            <div v-for="i in 3" :key="i" class="h-16 animate-pulse rounded-2xl bg-canvas" />
          </div>
          <p
            v-else-if="!column.bookings.length"
            class="mt-5 rounded-2xl bg-canvas p-4 text-center text-sm text-ink/50"
          >
            Agenda livre neste dia.
          </p>
          <ul v-else class="mt-5 space-y-2">
            <li
              v-for="booking in column.bookings"
              :key="booking.id"
              :class="booking.status === 'held' ? 'bg-amber-50 ring-amber-200/70' : 'bg-canvas ring-transparent'"
              class="flex items-center gap-4 rounded-2xl p-3 ring-1"
            >
              <span class="w-24 shrink-0 text-sm font-bold tabular-nums">
                {{ time(booking.starts_at, business.timezone) }}–{{
                  time(booking.ends_at, business.timezone)
                }}
              </span>
              <div class="min-w-0 flex-1">
                <p class="truncate font-semibold">{{ booking.customer_name }}</p>
                <p class="truncate text-xs text-ink/50">
                  {{ services.get(booking.service_id)?.name }} · {{ booking.customer_email }}
                </p>
              </div>
              <span
                v-if="booking.status === 'held'"
                class="rounded-full bg-amber-400 px-2.5 py-1 text-xs font-bold text-brand-950"
              >
                Oferta da fila
              </span>
              <span
                v-else-if="booking.status === 'completed'"
                class="rounded-full bg-brand-100 px-2.5 py-1 text-xs font-bold text-brand-800"
              >
                Atendido
              </span>
              <span
                v-else-if="booking.status === 'no_show'"
                class="rounded-full bg-rose-100 px-2.5 py-1 text-xs font-bold text-rose-700"
              >
                Faltou
              </span>
              <div v-else-if="started(booking)" class="flex shrink-0 gap-1">
                <LoaderCircle v-if="recording === booking.id" class="m-2.5 size-4 animate-spin text-ink/40" />
                <template v-else>
                  <button
                    class="grid size-9 place-items-center rounded-xl text-ink/40 transition hover:bg-brand-50 hover:text-brand-700"
                    :aria-label="`${booking.customer_name} compareceu`"
                    title="Compareceu"
                    @click="record(booking, 'completed')"
                  >
                    <UserCheck class="size-4" />
                  </button>
                  <button
                    class="grid size-9 place-items-center rounded-xl text-ink/40 transition hover:bg-rose-50 hover:text-rose-600"
                    :aria-label="`${booking.customer_name} faltou`"
                    title="Faltou"
                    @click="record(booking, 'no_show')"
                  >
                    <UserX class="size-4" />
                  </button>
                </template>
              </div>
              <button
                v-else
                :disabled="cancelling === booking.id"
                class="grid size-9 shrink-0 place-items-center rounded-xl text-ink/40 transition hover:bg-rose-50 hover:text-rose-600 disabled:opacity-50"
                :aria-label="`Cancelar o horário de ${booking.customer_name}`"
                @click="cancel(booking)"
              >
                <LoaderCircle v-if="cancelling === booking.id" class="size-4 animate-spin" />
                <Ban v-else class="size-4" />
              </button>
            </li>
          </ul>
        </section>
      </div>

      <UpcomingStats :business-id="business.id" :timezone="business.timezone" />
      <PastStats :business-id="business.id" :timezone="business.timezone" />
    </div>
  </div>

  <div v-else class="mx-auto max-w-6xl px-4 py-24 sm:px-6">
    <div class="h-64 animate-pulse rounded-3xl bg-white" />
  </div>
</template>
