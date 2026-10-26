<script setup lang="ts">
import { KeyRound, LoaderCircle, Plug, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { api, ApiError, type Webhook, type WebhookDelivery } from '../api'
import { time } from '../format'

const props = defineProps<{ businessId: string; timezone: string }>()

const EVENTS: Record<string, string> = {
  'booking.created': 'Agendamento',
  'booking.cancelled': 'Cancelamento',
  'booking.completed': 'Comparecimento',
  'booking.no_show': 'Falta',
  'waitlist.offer_created': 'Oferta da fila',
  'waitlist.offer_claimed': 'Oferta aceita',
  'waitlist.offer_expired': 'Oferta expirada',
}
const STATUS = {
  delivered: ['Entregue', 'bg-brand-100 text-brand-800'],
  pending: ['Tentando de novo', 'bg-amber-100 text-amber-800'],
  failed: ['Falhou', 'bg-rose-100 text-rose-700'],
} as const

const webhooks = ref<Webhook[]>()
const deliveries = ref<Record<string, WebhookDelivery[]>>({})
const url = ref('')
const events = ref<string[]>(['booking.created', 'booking.cancelled'])
const secret = ref('')
const saving = ref(false)
const error = ref('')

async function load() {
  webhooks.value = await api.webhooks(props.businessId)
  const lists = await Promise.all(
    webhooks.value.map((w) => api.webhookDeliveries(props.businessId, w.id)),
  )
  deliveries.value = Object.fromEntries(webhooks.value.map((w, i) => [w.id, lists[i]!.slice(0, 5)]))
}

async function add() {
  saving.value = true
  error.value = ''
  try {
    secret.value = (await api.createWebhook(props.businessId, url.value, events.value)).secret
    url.value = ''
    await load()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Não foi possível cadastrar'
  } finally {
    saving.value = false
  }
}

async function remove(webhook: Webhook) {
  if (!confirm(`Parar de enviar eventos para ${webhook.url}?`)) return
  await api.deleteWebhook(props.businessId, webhook.id)
  await load()
}

onMounted(load)
</script>

<template>
  <section class="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-ink/5">
    <h2 class="flex items-center gap-2 text-lg font-bold"><Plug class="size-5" /> Integrações</h2>
    <p class="text-sm text-ink/50">
      Webhooks assinados com HMAC-SHA256: o VagaCerta avisa outros sistemas (n8n, planilhas, CRM) a
      cada evento.
    </p>

    <form class="mt-5 space-y-3" @submit.prevent="add">
      <input
        v-model="url"
        type="url"
        required
        placeholder="https://seu-sistema.com/webhook"
        class="w-full rounded-xl bg-canvas px-4 py-2.5 ring-1 ring-ink/10 outline-none focus:ring-2 focus:ring-brand-500"
      />
      <div class="flex flex-wrap gap-2">
        <label
          v-for="(label, type) in EVENTS"
          :key="type"
          class="flex cursor-pointer items-center gap-1.5 rounded-full bg-canvas px-3 py-1.5 text-sm ring-1 ring-ink/10 has-checked:bg-brand-50 has-checked:text-brand-800 has-checked:ring-brand-300"
        >
          <input v-model="events" type="checkbox" :value="type" class="sr-only" />
          {{ label }}
        </label>
      </div>
      <button
        :disabled="saving || !events.length"
        class="inline-flex items-center gap-2 rounded-full bg-brand-700 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-brand-800 disabled:opacity-50"
      >
        <LoaderCircle v-if="saving" class="size-4 animate-spin" /> Adicionar webhook
      </button>
    </form>

    <p v-if="error" class="mt-3 rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
      {{ error }}
    </p>
    <div v-if="secret" class="mt-3 rounded-xl bg-amber-50 p-4 text-sm ring-1 ring-amber-200">
      <p class="flex items-center gap-2 font-semibold text-amber-900">
        <KeyRound class="size-4" /> Guarde o segredo: ele não aparece de novo.
      </p>
      <code class="mt-2 block break-all text-xs">{{ secret }}</code>
    </div>

    <ul v-if="webhooks?.length" class="mt-6 space-y-3">
      <li v-for="webhook in webhooks" :key="webhook.id" class="rounded-2xl bg-canvas p-4">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="truncate font-semibold">{{ webhook.url }}</p>
            <p class="text-xs text-ink/50">
              {{ webhook.events.map((e) => EVENTS[e] ?? e).join(' · ') }}
            </p>
          </div>
          <button
            class="grid size-9 shrink-0 place-items-center rounded-xl text-ink/40 hover:bg-rose-50 hover:text-rose-600"
            :aria-label="`Remover o webhook ${webhook.url}`"
            @click="remove(webhook)"
          >
            <Trash2 class="size-4" />
          </button>
        </div>
        <ul v-if="deliveries[webhook.id]?.length" class="mt-3 space-y-1.5">
          <li
            v-for="delivery in deliveries[webhook.id]"
            :key="delivery.id"
            class="flex items-center gap-2 text-xs"
          >
            <span :class="STATUS[delivery.status][1]" class="rounded-full px-2 py-0.5 font-bold">
              {{ STATUS[delivery.status][0] }}
            </span>
            <span class="font-medium">{{
              EVENTS[delivery.event_type] ?? delivery.event_type
            }}</span>
            <span class="text-ink/40">
              {{ time(delivery.updated_at, timezone) }} · {{ delivery.attempts }}
              {{ delivery.attempts === 1 ? 'tentativa' : 'tentativas' }}
              <template v-if="delivery.last_status_code"
                >· HTTP {{ delivery.last_status_code }}</template
              >
            </span>
          </li>
        </ul>
        <p v-else class="mt-3 text-xs text-ink/40">Nenhum evento enviado ainda.</p>
      </li>
    </ul>
  </section>
</template>
