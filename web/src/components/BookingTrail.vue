<script setup lang="ts">
import { History, ShieldCheck, X } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { api, ApiError, type Booking, type TrailEntry } from '../api'
import { longDate, time } from '../format'

const props = defineProps<{ booking: Booking; timezone: string }>()
defineEmits<{ close: [] }>()

const LABELS: Record<string, string> = {
  'booking.created': 'Agendado',
  'booking.cancelled': 'Cancelado',
  'booking.completed': 'Compareceu',
  'booking.no_show': 'Faltou',
  'waitlist.offer_created': 'Oferecido à lista de espera',
  'waitlist.offer_claimed': 'Oferta aceita pela fila',
  'waitlist.offer_expired': 'Oferta expirou',
}

const entries = ref<TrailEntry[]>()
const error = ref('')

onMounted(async () => {
  try {
    entries.value = await api.trail(props.booking.id)
  } catch (e) {
    error.value =
      e instanceof ApiError && e.status === 404
        ? 'Os eventos deste agendamento ainda estão chegando.'
        : 'Não foi possível carregar o histórico.'
  }
})
</script>

<template>
  <div
    class="fixed inset-0 z-40 grid place-items-center bg-ink/40 p-4"
    @click.self="$emit('close')"
  >
    <section
      class="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl"
      role="dialog"
      aria-label="Histórico do agendamento"
    >
      <header class="flex items-start justify-between gap-4">
        <div>
          <p class="flex items-center gap-2 text-sm font-semibold text-brand-700">
            <History class="size-4" /> Histórico
          </p>
          <h2 class="mt-1 text-lg font-bold">{{ booking.customer_name }}</h2>
          <p class="text-sm text-ink/50">
            {{ longDate(booking.starts_at, timezone) }}, {{ time(booking.starts_at, timezone) }}
          </p>
        </div>
        <button
          class="grid size-9 place-items-center rounded-xl text-ink/40 hover:bg-canvas"
          aria-label="Fechar"
          @click="$emit('close')"
        >
          <X class="size-5" />
        </button>
      </header>

      <p v-if="error" class="mt-6 rounded-2xl bg-canvas p-4 text-sm text-ink/60">{{ error }}</p>
      <div v-else-if="!entries" class="mt-6 h-32 animate-pulse rounded-2xl bg-canvas" />
      <ol v-else class="mt-6 space-y-4 border-l-2 border-brand-100 pl-5">
        <li v-for="entry in entries" :key="entry.seq" class="relative">
          <span
            class="absolute top-1.5 -left-[27px] size-3 rounded-full bg-brand-500 ring-4 ring-white"
          />
          <p class="font-semibold">{{ LABELS[entry.type] ?? entry.type }}</p>
          <p class="text-xs text-ink/50">
            {{ longDate(entry.occurred_at, timezone) }}, {{ time(entry.occurred_at, timezone) }} ·
            <span class="font-mono">{{ entry.hash.slice(0, 10) }}</span>
          </p>
        </li>
      </ol>

      <p class="mt-6 flex items-center gap-2 text-xs text-ink/40">
        <ShieldCheck class="size-4 text-brand-600" />
        Registro só de inserção: cada evento é encadeado ao anterior pelo hash.
      </p>
    </section>
  </div>
</template>
