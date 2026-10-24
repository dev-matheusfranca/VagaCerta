<script setup lang="ts">
import { BellRing, CalendarCheck, CalendarX2, Wallet } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { api, type DayStats } from '../api'
import { currency } from '../format'

const props = defineProps<{ businessId: string; timezone: string }>()

const today = new Intl.DateTimeFormat('en-CA', { timeZone: props.timezone }).format(new Date())
const dates = Array.from({ length: 14 }, (_, i) => {
  const date = new Date(`${today}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + i)
  return date.toISOString().slice(0, 10)
})
const stats = ref<DayStats[]>()

onMounted(async () => {
  stats.value = await api.stats(props.businessId, dates[0]!, dates[13]!)
})

const days = computed(() => {
  if (!stats.value) return undefined
  const byDay = new Map(stats.value.map((s) => [s.day, s]))
  return dates.map((iso) => {
    const date = new Date(`${iso}T12:00:00Z`)
    const day = byDay.get(iso)
    return {
      iso,
      weekday: date.toLocaleDateString('pt-BR', { weekday: 'short', timeZone: 'UTC' }).replace('.', ''),
      label: date.toLocaleDateString('pt-BR', { day: '2-digit', timeZone: 'UTC' }),
      booked: (day?.bookings ?? 0) - (day?.cancellations ?? 0),
      cancelled: day?.cancellations ?? 0,
      recovered: day?.offers_claimed ?? 0,
    }
  })
})
const totals = computed(() =>
  (stats.value ?? []).reduce(
    (sum, s) => ({
      bookings: sum.bookings + s.bookings,
      cancellations: sum.cancellations + s.cancellations,
      revenue: sum.revenue + s.revenue_cents,
      offers: sum.offers + s.offers,
      recovered: sum.recovered + s.offers_claimed,
      recoveredRevenue: sum.recoveredRevenue + s.recovered_revenue_cents,
    }),
    { bookings: 0, cancellations: 0, revenue: 0, offers: 0, recovered: 0, recoveredRevenue: 0 },
  ),
)
const peak = computed(() => Math.max(1, ...(days.value ?? []).map((d) => d.booked + d.cancelled)))
const kpis = computed(() => {
  const { bookings, cancellations, revenue, offers, recovered, recoveredRevenue } = totals.value
  return [
    {
      icon: CalendarCheck,
      label: 'Agendamentos confirmados',
      value: String(bookings - cancellations),
      hint: `${bookings} feitos no período`,
    },
    {
      icon: CalendarX2,
      label: 'Cancelamentos',
      value: String(cancellations),
      hint: bookings ? `${Math.round((cancellations / bookings) * 100)}% dos agendamentos` : '—',
    },
    { icon: Wallet, label: 'Receita prevista', value: currency(revenue), hint: 'Já sem os cancelados' },
    {
      icon: BellRing,
      label: 'Recuperados pela fila',
      value: String(recovered),
      hint: `${currency(recoveredRevenue)} de ${offers} ${offers === 1 ? 'oferta' : 'ofertas'}`,
    },
  ]
})
</script>

<template>
  <section class="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-ink/5">
    <div class="flex flex-wrap items-end justify-between gap-2">
      <div>
        <h2 class="text-lg font-bold">Próximos 14 dias</h2>
        <p class="text-sm text-ink/50">
          Projeção montada a partir dos eventos de agendamento e da lista de espera.
        </p>
      </div>
      <div class="flex items-center gap-4 text-xs font-semibold text-ink/60">
        <span class="flex items-center gap-1.5"><span class="size-2.5 rounded-sm bg-brand-500" /> Confirmados</span>
        <span class="flex items-center gap-1.5"><span class="size-2.5 rounded-sm bg-slate-300" /> Cancelados</span>
        <span class="flex items-center gap-1.5"><span class="size-2.5 rounded-full bg-amber-400" /> Recuperado pela fila</span>
      </div>
    </div>

    <div class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div v-for="kpi in kpis" :key="kpi.label" class="flex gap-3 rounded-2xl bg-canvas p-4">
        <span class="grid size-10 shrink-0 place-items-center rounded-xl bg-white text-brand-700">
          <component :is="kpi.icon" class="size-5" />
        </span>
        <div class="min-w-0">
          <p class="text-xs text-ink/50">{{ kpi.label }}</p>
          <p class="text-xl font-extrabold">{{ days ? kpi.value : '—' }}</p>
          <p class="truncate text-xs text-ink/40">{{ days ? kpi.hint : '' }}</p>
        </div>
      </div>
    </div>

    <div v-if="!days" class="mt-6 h-48 animate-pulse rounded-2xl bg-canvas" />
    <div v-else class="mt-6 flex h-48 items-end gap-1.5 sm:gap-2" role="img" aria-label="Agendamentos por dia">
      <div
        v-for="day in days"
        :key="day.iso"
        :title="`Dia ${day.label}: ${day.booked} confirmados, ${day.cancelled} cancelados, ${day.recovered} recuperados pela fila`"
        class="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1"
      >
        <span v-if="day.recovered" class="size-2 rounded-full bg-amber-400" />
        <div class="flex w-full max-w-10 flex-1 flex-col justify-end overflow-hidden rounded-lg bg-canvas">
          <div class="bg-slate-300" :style="{ height: `${(day.cancelled / peak) * 100}%` }" />
          <div class="bg-brand-500" :style="{ height: `${(day.booked / peak) * 100}%` }" />
        </div>
        <span class="text-[10px] font-semibold uppercase text-ink/40">{{ day.weekday }}</span>
        <span class="text-xs font-bold tabular-nums text-ink/70">{{ day.label }}</span>
      </div>
    </div>
  </section>
</template>
