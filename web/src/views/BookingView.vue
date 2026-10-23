<script setup lang="ts">
import {
  CalendarDays,
  CalendarPlus,
  CircleCheck,
  CircleX,
  Clock,
  LoaderCircle,
  MapPin,
  Store,
  Tag,
  User,
} from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { api, ApiError, type Booking, type BusinessDetail } from '../api'
import { longDate, price, time } from '../format'

const props = defineProps<{ id: string }>()

const booking = ref<Booking>()
const business = ref<BusinessDetail>()
const notFound = ref(false)
const cancelling = ref(false)
const error = ref('')

const confirmed = computed(() => booking.value?.status === 'confirmed')

const details = computed(() => {
  if (!booking.value || !business.value) return []
  const { starts_at, ends_at, service_id, professional_id } = booking.value
  const { timezone, services, professionals } = business.value
  const service = services.find((s) => s.id === service_id)
  return [
    { icon: Store, label: 'Local', value: business.value.name },
    { icon: Tag, label: 'Serviço', value: `${service?.name} · ${price(service?.price_cents ?? 0)}` },
    { icon: User, label: 'Profissional', value: professionals.find((p) => p.id === professional_id)?.name },
    { icon: CalendarDays, label: 'Data', value: longDate(starts_at, timezone) },
    { icon: Clock, label: 'Horário', value: `${time(starts_at, timezone)} – ${time(ends_at, timezone)}` },
    { icon: MapPin, label: 'Endereço', value: business.value.address },
  ]
})

onMounted(async () => {
  try {
    booking.value = await api.booking(props.id)
    business.value = await api.business(booking.value.business_id)
  } catch {
    notFound.value = true
  }
})

async function cancel() {
  if (!confirm('Cancelar este agendamento? O horário volta a ficar disponível.')) return
  cancelling.value = true
  try {
    booking.value = await api.cancelBooking(props.id)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Não foi possível cancelar'
  } finally {
    cancelling.value = false
  }
}
</script>

<template>
  <div class="relative">
    <div class="absolute inset-x-0 top-0 h-64 bg-brand-950" />
    <div class="relative mx-auto max-w-xl px-4 py-12 sm:px-6">
      <div v-if="notFound" class="rounded-3xl bg-white p-10 text-center shadow-xl">
        <CircleX class="mx-auto size-12 text-ink/30" />
        <p class="mt-4 text-lg font-semibold">Agendamento não encontrado.</p>
        <RouterLink to="/" class="mt-6 inline-block font-bold text-brand-700">
          Voltar ao início
        </RouterLink>
      </div>

      <article
        v-else-if="booking && business"
        class="overflow-hidden rounded-3xl bg-white shadow-2xl shadow-brand-900/10 ring-1 ring-ink/5"
      >
        <header
          :class="confirmed ? 'bg-brand-50' : 'bg-slate-100'"
          class="px-8 pt-10 pb-8 text-center"
        >
          <span
            :class="confirmed ? 'bg-brand-600 shadow-brand-600/30' : 'bg-slate-400 shadow-slate-400/30'"
            class="mx-auto grid size-16 place-items-center rounded-full text-white shadow-xl"
          >
            <component :is="confirmed ? CircleCheck : CircleX" class="size-8" />
          </span>
          <h1 class="mt-5 text-2xl font-extrabold tracking-tight">
            {{ confirmed ? 'Agendamento confirmado!' : 'Agendamento cancelado' }}
          </h1>
          <p class="mt-1 text-ink/60">
            {{
              confirmed
                ? `Tudo certo, ${booking.customer_name.split(' ')[0]}. Te esperamos!`
                : 'O horário foi liberado para outras pessoas.'
            }}
          </p>
        </header>

        <dl class="space-y-4 border-t-2 border-dashed border-ink/10 p-8">
          <div v-for="item in details" :key="item.label" class="flex items-center gap-4">
            <span
              class="grid size-10 shrink-0 place-items-center rounded-xl bg-canvas text-brand-700"
            >
              <component :is="item.icon" class="size-5" />
            </span>
            <div>
              <dt class="text-xs font-semibold tracking-wider text-ink/40 uppercase">
                {{ item.label }}
              </dt>
              <dd class="font-semibold first-letter:uppercase">{{ item.value }}</dd>
            </div>
          </div>
        </dl>

        <p v-if="error" class="mx-8 rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
          {{ error }}
        </p>
        <footer class="flex flex-col gap-3 p-6 sm:flex-row">
          <RouterLink
            :to="{ name: 'business', params: { id: business.id } }"
            class="flex flex-1 items-center justify-center gap-2 rounded-full bg-brand-700 py-3 font-bold text-white shadow-lg shadow-brand-700/25 transition hover:bg-brand-800"
          >
            <CalendarPlus class="size-5" /> Novo agendamento
          </RouterLink>
          <button
            v-if="confirmed"
            type="button"
            :disabled="cancelling"
            class="flex flex-1 items-center justify-center gap-2 rounded-full border border-rose-200 py-3 font-bold text-rose-600 transition hover:bg-rose-50 disabled:opacity-50"
            @click="cancel"
          >
            <LoaderCircle v-if="cancelling" class="size-5 animate-spin" />
            Cancelar agendamento
          </button>
        </footer>
      </article>

      <div v-else class="h-[32rem] animate-pulse rounded-3xl bg-white" />
    </div>
  </div>
</template>
