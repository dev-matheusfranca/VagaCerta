<script setup lang="ts">
import {
  BellRing,
  CalendarDays,
  CircleX,
  Clock,
  LoaderCircle,
  MapPin,
  Store,
  Tag,
  User,
} from 'lucide-vue-next'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, ApiError, type Offer } from '../api'
import { longDate, price, time } from '../format'

const props = defineProps<{ id: string }>()
const router = useRouter()

const offer = ref<Offer>()
const notFound = ref(false)
const claiming = ref(false)
const error = ref('')
const now = ref(Date.now())
const ticker = setInterval(() => (now.value = Date.now()), 1000)
onUnmounted(() => clearInterval(ticker))

const secondsLeft = computed(() =>
  offer.value
    ? Math.max(0, Math.floor((new Date(offer.value.expires_at).getTime() - now.value) / 1000))
    : 0,
)
const open = computed(() => offer.value?.status === 'pending' && secondsLeft.value > 0)
const countdown = computed(
  () =>
    `${String(Math.floor(secondsLeft.value / 60)).padStart(2, '0')}:${String(secondsLeft.value % 60).padStart(2, '0')}`,
)

const details = computed(() => {
  if (!offer.value) return []
  const { starts_at, ends_at, entry } = offer.value
  const { timezone, ...d } = entry.details
  return [
    { icon: Store, label: 'Local', value: d.business_name },
    { icon: Tag, label: 'Serviço', value: `${d.service_name} · ${price(d.price_cents)}` },
    { icon: User, label: 'Profissional', value: d.professional_name },
    { icon: CalendarDays, label: 'Data', value: longDate(starts_at, timezone) },
    { icon: Clock, label: 'Horário', value: `${time(starts_at, timezone)} – ${time(ends_at, timezone)}` },
    { icon: MapPin, label: 'Endereço', value: d.business_address },
  ]
})

onMounted(async () => {
  try {
    offer.value = await api.offer(props.id)
  } catch {
    notFound.value = true
    return
  }
  if (offer.value.status === 'claimed') {
    await router.replace({ name: 'booking', params: { id: offer.value.booking_id } })
  }
})

async function claim() {
  claiming.value = true
  error.value = ''
  try {
    const claimed = await api.claimOffer(props.id)
    await router.push({ name: 'booking', params: { id: claimed.booking_id } })
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Não foi possível confirmar o horário'
    offer.value = await api.offer(props.id)
  } finally {
    claiming.value = false
  }
}
</script>

<template>
  <div class="relative">
    <div class="absolute inset-x-0 top-0 h-64 bg-brand-950" />
    <div class="relative mx-auto max-w-xl px-4 py-12 sm:px-6">
      <div v-if="notFound" class="rounded-3xl bg-white p-10 text-center shadow-xl">
        <CircleX class="mx-auto size-12 text-ink/30" />
        <p class="mt-4 text-lg font-semibold">Oferta não encontrada.</p>
        <RouterLink to="/" class="mt-6 inline-block font-bold text-brand-700">
          Voltar ao início
        </RouterLink>
      </div>

      <article
        v-else-if="offer"
        class="overflow-hidden rounded-3xl bg-white shadow-2xl shadow-brand-900/10 ring-1 ring-ink/5"
      >
        <header :class="open ? 'bg-amber-50' : 'bg-slate-100'" class="px-8 pt-10 pb-8 text-center">
          <span
            :class="open ? 'bg-amber-400 text-brand-950 shadow-amber-500/30' : 'bg-slate-400 text-white'"
            class="mx-auto grid size-16 place-items-center rounded-full shadow-xl"
          >
            <component :is="open ? BellRing : CircleX" class="size-8" />
          </span>
          <h1 class="mt-5 text-2xl font-extrabold tracking-tight">
            {{
              open
                ? `Uma vaga abriu pra você, ${offer.entry.customer_name.split(' ')[0]}!`
                : 'Essa oferta expirou'
            }}
          </h1>
          <p class="mt-1 text-ink/60">
            {{
              open
                ? 'Alguém cancelou e guardamos este horário para você.'
                : 'O horário foi oferecido à próxima pessoa da fila.'
            }}
          </p>
          <p
            v-if="open"
            class="mt-5 inline-flex items-baseline gap-2 rounded-2xl bg-white px-5 py-3 ring-1 ring-amber-200"
          >
            <span class="text-sm font-semibold text-ink/50">Expira em</span>
            <span class="text-3xl font-extrabold tabular-nums text-amber-600">{{ countdown }}</span>
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
        <footer class="p-6">
          <button
            v-if="open"
            type="button"
            :disabled="claiming"
            class="flex w-full items-center justify-center gap-2 rounded-full bg-amber-400 py-3.5 font-bold text-brand-950 shadow-lg shadow-amber-500/25 transition hover:bg-amber-300 disabled:opacity-50"
            @click="claim"
          >
            <LoaderCircle v-if="claiming" class="size-5 animate-spin" />
            Quero esse horário
          </button>
          <RouterLink
            v-else
            :to="{ name: 'home', hash: '#estabelecimentos' }"
            class="flex w-full items-center justify-center rounded-full bg-brand-700 py-3.5 font-bold text-white transition hover:bg-brand-800"
          >
            Ver outros horários
          </RouterLink>
        </footer>
      </article>

      <div v-else class="h-[32rem] animate-pulse rounded-3xl bg-white" />
    </div>
  </div>
</template>
