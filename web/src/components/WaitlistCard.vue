<script setup lang="ts">
import { BellRing, Check, LoaderCircle } from 'lucide-vue-next'
import { ref } from 'vue'
import { api, ApiError } from '../api'

const props = defineProps<{
  businessId: string
  professionalId: string
  serviceId: string
  day: string
}>()

const name = ref('')
const email = ref('')
const position = ref<number>()
const sending = ref(false)
const error = ref('')

async function join() {
  sending.value = true
  error.value = ''
  try {
    const entry = await api.joinWaitlist({
      business_id: props.businessId,
      professional_id: props.professionalId,
      service_id: props.serviceId,
      day: props.day,
      customer_name: name.value,
      customer_email: email.value,
    })
    position.value = entry.position
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Não foi possível entrar na lista'
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <div class="rounded-2xl bg-amber-50 p-5 ring-1 ring-amber-200/70">
    <div class="flex items-start gap-3">
      <span class="grid size-10 shrink-0 place-items-center rounded-xl bg-amber-400 text-brand-950">
        <Check v-if="position" class="size-5" />
        <BellRing v-else class="size-5" />
      </span>
      <div v-if="position">
        <p class="font-bold">Você está na lista! Sua posição: {{ position }}º</p>
        <p class="mt-1 text-sm text-ink/60">
          Se alguém cancelar, guardamos o horário para você por alguns minutos e avisamos por
          e-mail.
        </p>
      </div>
      <div v-else>
        <p class="font-bold">Dia cheio? Entre na lista de espera.</p>
        <p class="mt-1 text-sm text-ink/60">
          Se alguém cancelar, o horário fica guardado para você e avisamos por e-mail.
        </p>
      </div>
    </div>

    <form v-if="!position" class="mt-4" @submit.prevent="join">
      <div class="grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
        <input
          v-model="name"
          required
          minlength="2"
          autocomplete="name"
          placeholder="Seu nome"
          class="w-full rounded-xl border border-amber-200 bg-white px-4 py-2.5 outline-none transition focus:border-amber-400 focus:ring-4 focus:ring-amber-400/20"
        />
        <input
          v-model="email"
          type="email"
          required
          autocomplete="email"
          placeholder="voce@email.com"
          class="w-full rounded-xl border border-amber-200 bg-white px-4 py-2.5 outline-none transition focus:border-amber-400 focus:ring-4 focus:ring-amber-400/20"
        />
        <button
          :disabled="sending"
          class="flex items-center justify-center gap-2 rounded-xl bg-amber-400 px-5 py-2.5 font-bold text-brand-950 transition hover:bg-amber-300 disabled:opacity-50"
        >
          <LoaderCircle v-if="sending" class="size-4 animate-spin" />
          Entrar na fila
        </button>
      </div>
      <p v-if="error" class="mt-3 text-sm font-medium text-rose-700">{{ error }}</p>
    </form>
  </div>
</template>
