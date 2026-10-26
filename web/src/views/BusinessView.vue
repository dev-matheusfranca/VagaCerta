<script setup lang="ts">
import { ArrowLeft, CalendarX2, Check, Clock, LoaderCircle, MapPin } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, ApiError, type BusinessDetail } from '../api'
import WaitlistCard from '../components/WaitlistCard.vue'
import { category, initials, longDate, price, time } from '../format'

const props = defineProps<{ id: string }>()
const router = useRouter()

const business = ref<BusinessDetail>()
const notFound = ref(false)
const serviceId = ref('')
const professionalId = ref('')
const day = ref('')
const slots = ref<string[]>()
const slot = ref('')
const customerName = ref('')
const customerEmail = ref('')
const submitting = ref(false)
const error = ref('')

const service = computed(() => business.value?.services.find((s) => s.id === serviceId.value))
const professional = computed(() =>
  business.value?.professionals.find((p) => p.id === professionalId.value),
)

const days = computed(() => {
  if (!business.value) return []
  const today = new Intl.DateTimeFormat('en-CA', { timeZone: business.value.timezone }).format(
    new Date(),
  )
  const workdays = new Set(professional.value?.working_hours.map((h) => h.weekday))
  return Array.from({ length: 14 }, (_, i) => {
    const date = new Date(`${today}T12:00:00Z`)
    date.setUTCDate(date.getUTCDate() + i)
    const label = (options: Intl.DateTimeFormatOptions) =>
      date.toLocaleDateString('pt-BR', { timeZone: 'UTC', ...options }).replace('.', '')
    return {
      iso: date.toISOString().slice(0, 10),
      weekday: label({ weekday: 'short' }),
      day: date.getUTCDate(),
      month: label({ month: 'short' }),
      open: workdays.has((date.getUTCDay() + 6) % 7),
    }
  })
})

const selection = computed(() => ({
  business_id: props.id,
  professional_id: professionalId.value,
  service_id: serviceId.value,
  date: day.value,
}))

async function loadSlots() {
  const params = selection.value
  slot.value = ''
  slots.value = undefined
  const { slots: free } = await api.availability(params)
  // Descarta respostas atrasadas quando a pessoa troca de dia/serviço antes da anterior chegar.
  if (params === selection.value) slots.value = free
}

watch(
  professionalId,
  () => {
    day.value = days.value.find((d) => d.open)?.iso ?? ''
  },
  { flush: 'sync' },
)
watch(selection, loadSlots)

onMounted(async () => {
  try {
    business.value = await api.business(props.id)
  } catch {
    notFound.value = true
    return
  }
  serviceId.value = business.value.services[0]?.id ?? ''
  professionalId.value = business.value.professionals[0]?.id ?? ''
})

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    const booking = await api.createBooking({
      business_id: props.id,
      professional_id: professionalId.value,
      service_id: serviceId.value,
      starts_at: slot.value,
      customer_name: customerName.value,
      customer_email: customerEmail.value,
    })
    await router.push({ name: 'booking', params: { id: booking.id } })
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Não foi possível concluir o agendamento'
    if (e instanceof ApiError && e.status === 409) await loadSlots()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div v-if="notFound" class="mx-auto max-w-6xl px-4 py-24 text-center sm:px-6">
    <CalendarX2 class="mx-auto size-12 text-ink/30" />
    <p class="mt-4 text-lg font-semibold">Estabelecimento não encontrado.</p>
    <RouterLink to="/" class="mt-6 inline-block font-bold text-brand-700">Voltar ao início</RouterLink>
  </div>

  <div v-else-if="business">
    <section class="relative overflow-hidden bg-brand-950 text-white">
      <div
        class="pointer-events-none absolute -top-32 right-0 size-96 rounded-full bg-brand-500/25 blur-3xl"
      />
      <div class="relative mx-auto max-w-6xl px-4 pt-6 pb-24 sm:px-6">
        <RouterLink
          :to="{ name: 'home', hash: '#estabelecimentos' }"
          class="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-200 transition hover:text-white"
        >
          <ArrowLeft class="size-4" /> Estabelecimentos
        </RouterLink>
        <div class="mt-6 flex items-center gap-5">
          <span
            :class="category(business.category).tone"
            class="grid size-16 shrink-0 place-items-center rounded-2xl bg-linear-to-br shadow-lg ring-4 ring-white/10"
          >
            <component :is="category(business.category).icon" class="size-8" />
          </span>
          <div>
            <p class="text-sm font-semibold text-amber-400">{{ category(business.category).label }}</p>
            <h1 class="text-2xl font-extrabold tracking-tight sm:text-3xl">{{ business.name }}</h1>
            <p class="mt-1 flex items-center gap-1.5 text-sm text-brand-100/70">
              <MapPin class="size-4 shrink-0" />{{ business.address }}
            </p>
          </div>
        </div>
      </div>
    </section>

    <div
      class="relative mx-auto -mt-14 grid max-w-6xl gap-6 px-4 pb-16 sm:px-6 lg:grid-cols-[1fr_22rem]"
    >
      <div class="min-w-0 space-y-6">
        <section class="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-ink/5">
          <h2 class="flex items-center gap-3 font-bold">
            <span
              class="grid size-7 place-items-center rounded-full bg-brand-600 text-sm text-white"
            >
              1
            </span>
            Escolha o serviço
          </h2>
          <div class="mt-4 grid gap-3 sm:grid-cols-2">
            <button
              v-for="s in business.services"
              :key="s.id"
              type="button"
              :class="
                s.id === serviceId
                  ? 'border-brand-500 bg-brand-50 ring-4 ring-brand-500/15'
                  : 'border-ink/10 hover:border-brand-300'
              "
              class="flex items-center justify-between gap-4 rounded-2xl border p-4 text-left transition"
              @click="serviceId = s.id"
            >
              <span>
                <span class="block font-semibold">{{ s.name }}</span>
                <span class="mt-0.5 flex items-center gap-1 text-sm text-ink/50">
                  <Clock class="size-3.5" />{{ s.duration_minutes }} min
                </span>
              </span>
              <span class="font-bold whitespace-nowrap text-brand-700">
                {{ price(s.price_cents) }}
              </span>
            </button>
          </div>
        </section>

        <section class="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-ink/5">
          <h2 class="flex items-center gap-3 font-bold">
            <span
              class="grid size-7 place-items-center rounded-full bg-brand-600 text-sm text-white"
            >
              2
            </span>
            Com quem?
          </h2>
          <div class="mt-4 flex flex-wrap gap-3">
            <button
              v-for="p in business.professionals"
              :key="p.id"
              type="button"
              :class="
                p.id === professionalId
                  ? 'border-brand-500 bg-brand-50 ring-4 ring-brand-500/15'
                  : 'border-ink/10 hover:border-brand-300'
              "
              class="flex items-center gap-3 rounded-2xl border py-2.5 pr-5 pl-2.5 text-left transition"
              @click="professionalId = p.id"
            >
              <span
                class="grid size-10 place-items-center rounded-full bg-linear-to-br from-brand-400 to-brand-700 text-sm font-bold text-white"
              >
                {{ initials(p.name) }}
              </span>
              <span>
                <span class="block text-sm font-semibold">{{ p.name }}</span>
                <span class="block text-xs text-ink/50">{{ p.specialty }}</span>
              </span>
            </button>
          </div>
        </section>

        <section class="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-ink/5">
          <h2 class="flex items-center gap-3 font-bold">
            <span
              class="grid size-7 place-items-center rounded-full bg-brand-600 text-sm text-white"
            >
              3
            </span>
            Quando?
          </h2>
          <div class="-mx-6 mt-4 flex gap-2 overflow-x-auto px-6 pb-2 [scrollbar-width:thin]">
            <button
              v-for="d in days"
              :key="d.iso"
              type="button"
              :disabled="!d.open"
              :class="
                d.iso === day
                  ? 'bg-brand-700 text-white shadow-lg shadow-brand-700/30'
                  : 'bg-canvas hover:bg-brand-50'
              "
              class="flex w-16 shrink-0 flex-col items-center rounded-2xl py-3 transition disabled:cursor-not-allowed disabled:opacity-35"
              @click="day = d.iso"
            >
              <span class="text-xs font-semibold uppercase opacity-70">{{ d.weekday }}</span>
              <span class="text-xl font-extrabold">{{ d.day }}</span>
              <span class="text-xs opacity-70">{{ d.month }}</span>
            </button>
          </div>

          <div class="mt-5">
            <div v-if="!slots" class="grid grid-cols-3 gap-2 sm:grid-cols-5">
              <span v-for="i in 10" :key="i" class="h-11 animate-pulse rounded-xl bg-canvas" />
            </div>
            <div v-else-if="!slots.length" class="space-y-3">
              <p class="flex items-center gap-3 rounded-2xl bg-canvas p-4 text-sm text-ink/60">
                <CalendarX2 class="size-5 shrink-0" /> Nenhum horário livre neste dia.
              </p>
              <WaitlistCard
                :key="`${professionalId}-${serviceId}-${day}`"
                :business-id="id"
                :professional-id="professionalId"
                :service-id="serviceId"
                :day="day"
              />
            </div>
            <div v-else class="grid grid-cols-3 gap-2 sm:grid-cols-5">
              <button
                v-for="s in slots"
                :key="s"
                type="button"
                :class="
                  s === slot
                    ? 'bg-amber-400 text-brand-950 shadow-md shadow-amber-500/30'
                    : 'bg-brand-50 text-brand-800 hover:bg-brand-100'
                "
                class="h-11 rounded-xl text-sm font-bold transition"
                @click="slot = s"
              >
                {{ time(s, business.timezone) }}
              </button>
            </div>
          </div>
        </section>
      </div>

      <aside class="lg:sticky lg:top-24 lg:self-start">
        <form
          class="rounded-3xl bg-white p-6 shadow-xl shadow-brand-900/5 ring-1 ring-ink/5"
          @submit.prevent="submit"
        >
          <h2 class="font-bold">Resumo do agendamento</h2>
          <dl class="mt-4 space-y-3 text-sm">
            <div class="flex justify-between gap-4">
              <dt class="text-ink/50">Serviço</dt>
              <dd class="text-right font-semibold">{{ service?.name ?? '—' }}</dd>
            </div>
            <div class="flex justify-between gap-4">
              <dt class="text-ink/50">Profissional</dt>
              <dd class="text-right font-semibold">{{ professional?.name ?? '—' }}</dd>
            </div>
            <div class="flex justify-between gap-4">
              <dt class="text-ink/50">Quando</dt>
              <dd class="text-right font-semibold first-letter:uppercase">
                {{
                  slot
                    ? `${longDate(slot, business.timezone)}, ${time(slot, business.timezone)}`
                    : 'Escolha um horário'
                }}
              </dd>
            </div>
          </dl>
          <div
            class="my-5 flex items-baseline justify-between border-t border-dashed border-ink/15 pt-4"
          >
            <span class="text-sm text-ink/50">Total</span>
            <span class="text-2xl font-extrabold text-brand-700">
              {{ service ? price(service.price_cents) : '—' }}
            </span>
          </div>

          <label class="block text-sm font-semibold">
            Seu nome
            <input
              v-model="customerName"
              required
              minlength="2"
              autocomplete="name"
              placeholder="Como devemos te chamar?"
              class="mt-1.5 w-full rounded-xl border border-ink/10 bg-canvas px-4 py-2.5 font-normal outline-none transition focus:border-brand-500 focus:bg-white focus:ring-4 focus:ring-brand-500/15"
            />
          </label>
          <label class="mt-3 block text-sm font-semibold">
            E-mail
            <input
              v-model="customerEmail"
              type="email"
              required
              autocomplete="email"
              placeholder="voce@email.com"
              class="mt-1.5 w-full rounded-xl border border-ink/10 bg-canvas px-4 py-2.5 font-normal outline-none transition focus:border-brand-500 focus:bg-white focus:ring-4 focus:ring-brand-500/15"
            />
          </label>

          <p v-if="error" class="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
            {{ error }}
          </p>
          <button
            type="submit"
            :disabled="!slot || submitting"
            class="mt-5 flex w-full items-center justify-center gap-2 rounded-full bg-brand-700 py-3.5 font-bold text-white shadow-lg shadow-brand-700/25 transition hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <LoaderCircle v-if="submitting" class="size-5 animate-spin" />
            <Check v-else class="size-5" />
            Confirmar agendamento
          </button>
        </form>
      </aside>
    </div>
  </div>
</template>
