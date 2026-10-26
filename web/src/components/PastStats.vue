<script setup lang="ts">
import { CalendarCheck, Clock, Gauge, UserX } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { api, type DayStats, type HourStats } from '../api'

const props = defineProps<{ businessId: string; timezone: string }>()

const WEEKDAYS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']

const today = new Intl.DateTimeFormat('en-CA', { timeZone: props.timezone }).format(new Date())
function shift(iso: string, days: number) {
  const date = new Date(`${iso}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

const stats = ref<DayStats[]>()
const hours = ref<HourStats[]>()

onMounted(async () => {
  ;[stats.value, hours.value] = await Promise.all([
    api.stats(props.businessId, shift(today, -30), shift(today, -1)),
    api.peakHours(props.businessId),
  ])
})

const kpis = computed(() => {
  const sum = (pick: (s: DayStats) => number) =>
    (stats.value ?? []).reduce((n, s) => n + pick(s), 0)
  const completed = sum((s) => s.completed)
  const noShows = sum((s) => s.no_shows)
  const capacity = sum((s) => s.capacity_minutes ?? 0)
  const peak = (hours.value ?? []).reduce<HourStats | undefined>(
    (best, h) => (!best || h.bookings > best.bookings ? h : best),
    undefined,
  )
  const percent = (part: number, whole: number) =>
    whole ? `${Math.round((part / whole) * 100)}%` : '—'
  return [
    {
      icon: CalendarCheck,
      label: 'Atendimentos',
      value: String(completed),
      hint: 'Nos últimos 30 dias',
    },
    {
      icon: UserX,
      label: 'Faltas',
      value: String(noShows),
      hint: `${percent(noShows, completed + noShows)} de quem tinha horário`,
    },
    {
      icon: Gauge,
      label: 'Ocupação média',
      value: percent(
        sum((s) => s.booked_minutes),
        capacity,
      ),
      hint: 'Do tempo de expediente',
    },
    {
      icon: Clock,
      label: 'Horário de pico',
      value: peak ? `${WEEKDAYS[peak.weekday]}, ${peak.hour}h` : '—',
      hint: peak ? `${peak.bookings} agendamentos nesse horário` : 'Sem agendamentos ainda',
    },
  ]
})

// Mapa de calor: dias da semana com movimento nas linhas, horas nas colunas.
const heatmap = computed(() => {
  if (!hours.value?.length) return undefined
  const counts = new Map(hours.value.map((h) => [`${h.weekday}-${h.hour}`, h.bookings]))
  const max = Math.max(...hours.value.map((h) => h.bookings))
  const hourRange = hours.value.map((h) => h.hour)
  const columns = Array.from(
    { length: Math.max(...hourRange) - Math.min(...hourRange) + 1 },
    (_, i) => Math.min(...hourRange) + i,
  )
  const weekdays = [...new Set(hours.value.map((h) => h.weekday))].sort()
  return {
    columns,
    rows: weekdays.map((weekday) => ({
      label: WEEKDAYS[weekday],
      cells: columns.map((hour) => {
        const bookings = counts.get(`${weekday}-${hour}`) ?? 0
        return { hour, bookings, strength: Math.round((bookings / max) * 100) }
      }),
    })),
  }
})
</script>

<template>
  <section class="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-ink/5">
    <h2 class="text-lg font-bold">Últimos 30 dias</h2>
    <p class="text-sm text-ink/50">
      Comparecimento registrado na agenda e horários mais procurados.
    </p>

    <div class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div v-for="kpi in kpis" :key="kpi.label" class="flex gap-3 rounded-2xl bg-canvas p-4">
        <span class="grid size-10 shrink-0 place-items-center rounded-xl bg-white text-brand-700">
          <component :is="kpi.icon" class="size-5" />
        </span>
        <div class="min-w-0">
          <p class="text-xs text-ink/50">{{ kpi.label }}</p>
          <p class="text-xl font-extrabold">{{ stats ? kpi.value : '—' }}</p>
          <p class="truncate text-xs text-ink/40">{{ stats ? kpi.hint : '' }}</p>
        </div>
      </div>
    </div>

    <div v-if="!hours" class="mt-6 h-40 animate-pulse rounded-2xl bg-canvas" />
    <div v-else-if="heatmap" class="mt-6 overflow-x-auto">
      <table
        class="w-full border-separate border-spacing-1"
        aria-label="Agendamentos por dia e hora"
      >
        <thead>
          <tr>
            <th />
            <th
              v-for="hour in heatmap.columns"
              :key="hour"
              class="text-[10px] font-semibold text-ink/40"
            >
              {{ hour }}h
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in heatmap.rows" :key="row.label">
            <th class="pr-2 text-left text-xs font-semibold text-ink/50">{{ row.label }}</th>
            <td
              v-for="cell in row.cells"
              :key="cell.hour"
              :title="`${row.label}, ${cell.hour}h: ${cell.bookings} agendamentos`"
              :style="{
                backgroundColor: `color-mix(in oklab, var(--color-brand-600) ${cell.strength}%, var(--color-canvas))`,
              }"
              class="h-8 min-w-8 rounded-md"
            />
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
