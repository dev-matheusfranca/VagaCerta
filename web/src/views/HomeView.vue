<script setup lang="ts">
import { ArrowRight, BellRing, CalendarClock, MapPin, ShieldCheck, Zap } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { api, type Business } from '../api'
import { category } from '../format'

const businesses = ref<Business[]>()
const error = ref('')

onMounted(async () => {
  try {
    businesses.value = await api.businesses()
  } catch {
    error.value = 'Não foi possível carregar os estabelecimentos. Os serviços estão rodando?'
  }
})

const preview = [
  { time: '09:00', state: 'taken' },
  { time: '09:30', state: 'free' },
  { time: '10:00', state: 'taken' },
  { time: '10:30', state: 'free' },
  { time: '11:00', state: 'released' },
  { time: '11:30', state: 'free' },
  { time: '14:00', state: 'taken' },
  { time: '14:30', state: 'free' },
  { time: '15:00', state: 'free' },
] as const

const slotStyle = {
  taken: 'bg-slate-100 text-ink/30 line-through',
  free: 'bg-brand-50 text-brand-700 ring-1 ring-brand-200',
  released: 'bg-amber-400 text-brand-950 shadow-md shadow-amber-500/30',
}

const features = [
  {
    icon: Zap,
    title: 'Disponibilidade em tempo real',
    text: 'Os horários livres são calculados na hora, a partir do expediente de cada profissional.',
  },
  {
    icon: ShieldCheck,
    title: 'Zero conflito de agenda',
    text: 'Mesmo com várias pessoas clicando ao mesmo tempo, cada horário tem um único dono.',
  },
  {
    icon: CalendarClock,
    title: 'Sem troca de mensagens',
    text: 'Serviço, profissional e horário escolhidos em poucos cliques, a qualquer hora do dia.',
  },
]
</script>

<template>
  <section class="relative overflow-hidden bg-brand-950 text-white">
    <div
      class="pointer-events-none absolute -top-40 -right-32 size-144 rounded-full bg-brand-500/25 blur-3xl"
    />
    <div
      class="pointer-events-none absolute -bottom-48 -left-24 size-112 rounded-full bg-amber-400/10 blur-3xl"
    />

    <div
      class="relative mx-auto grid max-w-6xl items-center gap-14 px-4 pt-16 pb-24 sm:px-6 lg:grid-cols-[1.15fr_1fr] lg:pt-24 lg:pb-32"
    >
      <div>
        <span
          class="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-semibold text-brand-200"
        >
          <span class="size-1.5 rounded-full bg-amber-400" />
          Agendamento online para pequenos negócios
        </span>
        <h1
          class="mt-6 text-4xl leading-[1.08] font-extrabold tracking-tight text-balance sm:text-5xl lg:text-6xl"
        >
          O horário certo, <span class="text-amber-400">sem troca</span> de mensagens.
        </h1>
        <p class="mt-5 max-w-xl text-lg text-brand-100/75">
          Barbearias, salões, clínicas e estúdios com a agenda aberta 24 horas. Você escolhe o
          serviço, o profissional e o horário — e pronto.
        </p>
        <a
          href="#estabelecimentos"
          class="mt-8 inline-flex items-center gap-2 rounded-full bg-amber-400 px-6 py-3 font-bold text-brand-950 shadow-lg shadow-amber-500/20 transition hover:-translate-y-0.5 hover:bg-amber-300"
        >
          Encontrar um horário <ArrowRight class="size-4" />
        </a>
      </div>

      <div class="relative mx-auto w-full max-w-md" aria-hidden="true">
        <div class="absolute inset-0 -rotate-3 rounded-3xl bg-brand-500/30" />
        <div class="relative rounded-3xl bg-white p-6 text-ink shadow-2xl">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs font-semibold tracking-wider text-ink/40 uppercase">Terça-feira</p>
              <p class="text-lg font-bold">Barbearia Navalha de Ouro</p>
            </div>
            <span
              class="shrink-0 rounded-full bg-brand-50 px-3 py-1 text-xs font-bold whitespace-nowrap text-brand-700"
            >
              6 livres
            </span>
          </div>
          <div class="mt-5 grid grid-cols-3 gap-2">
            <span
              v-for="slot in preview"
              :key="slot.time"
              :class="slotStyle[slot.state]"
              class="relative rounded-xl py-2.5 text-center text-sm font-semibold"
            >
              {{ slot.time }}
              <span v-if="slot.state === 'released'" class="absolute -top-1 -right-1 flex size-3">
                <span class="absolute size-full animate-ping rounded-full bg-amber-400 opacity-75" />
                <span class="relative size-3 rounded-full bg-amber-500 ring-2 ring-white" />
              </span>
            </span>
          </div>
          <div class="mt-5 flex items-center gap-3 rounded-2xl bg-amber-50 p-3 text-sm">
            <span
              class="grid size-9 shrink-0 place-items-center rounded-xl bg-amber-400 text-brand-950"
            >
              <BellRing class="size-4" />
            </span>
            <p>
              <strong>Vaga liberada às 11:00</strong><br />
              <span class="text-ink/60">Um cliente cancelou e o horário voltou para a agenda.</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="relative mx-auto -mt-12 max-w-6xl px-4 sm:px-6">
    <div
      class="grid gap-6 rounded-3xl bg-white p-6 shadow-xl shadow-ink/5 ring-1 ring-ink/5 sm:grid-cols-3 sm:p-8"
    >
      <div v-for="feature in features" :key="feature.title" class="flex gap-4">
        <span
          class="grid size-11 shrink-0 place-items-center rounded-2xl bg-brand-50 text-brand-700"
        >
          <component :is="feature.icon" class="size-5" />
        </span>
        <div>
          <h3 class="font-bold">{{ feature.title }}</h3>
          <p class="mt-1 text-sm text-ink/60">{{ feature.text }}</p>
        </div>
      </div>
    </div>
  </section>

  <section id="estabelecimentos" class="mx-auto max-w-6xl scroll-mt-20 px-4 py-16 sm:px-6">
    <p class="text-sm font-bold tracking-wider text-brand-600 uppercase">Agende agora</p>
    <h2 class="mt-1 text-3xl font-extrabold tracking-tight">Estabelecimentos</h2>

    <p v-if="error" class="mt-8 rounded-2xl bg-rose-50 p-4 text-rose-700">{{ error }}</p>
    <div v-else-if="!businesses" class="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
      <div v-for="i in 4" :key="i" class="h-72 animate-pulse rounded-3xl bg-white" />
    </div>
    <div v-else class="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
      <RouterLink
        v-for="business in businesses"
        :key="business.id"
        :to="{ name: 'business', params: { id: business.id } }"
        class="group flex flex-col overflow-hidden rounded-3xl bg-white ring-1 ring-ink/5 transition hover:-translate-y-1 hover:shadow-xl hover:shadow-brand-900/10"
      >
        <div
          :class="category(business.category).tone"
          class="relative grid h-28 place-items-center bg-linear-to-br text-white"
        >
          <component
            :is="category(business.category).icon"
            class="size-10 opacity-90 transition group-hover:scale-110"
            :stroke-width="1.75"
          />
          <span
            class="absolute top-3 left-3 rounded-full bg-white/20 px-2.5 py-0.5 text-xs font-semibold backdrop-blur"
          >
            {{ category(business.category).label }}
          </span>
        </div>
        <div class="flex flex-1 flex-col p-5">
          <h3 class="leading-snug font-bold">{{ business.name }}</h3>
          <p class="mt-1.5 line-clamp-2 text-sm text-ink/60">{{ business.description }}</p>
          <p class="mt-4 flex items-start gap-1.5 text-xs text-ink/50">
            <MapPin class="mt-px size-3.5 shrink-0" />{{ business.address }}
          </p>
          <span
            class="mt-auto inline-flex items-center gap-1.5 pt-5 text-sm font-bold text-brand-700"
          >
            Ver horários
            <ArrowRight class="size-4 transition group-hover:translate-x-1" />
          </span>
        </div>
      </RouterLink>
    </div>
  </section>
</template>
