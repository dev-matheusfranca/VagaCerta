<script setup lang="ts">
import { BotMessageSquare, SendHorizontal, Wrench } from 'lucide-vue-next'
import { computed, nextTick, ref } from 'vue'
import { api, ApiError, type ChatMessage } from '../api'

const STEPS: Record<string, string> = {
  list_businesses: 'Consultou os estabelecimentos',
  get_business: 'Viu serviços e profissionais',
  find_slots: 'Procurou horários livres',
  book_appointment: 'Fez o agendamento',
  join_waitlist: 'Entrou na lista de espera',
  cancel_booking: 'Cancelou o agendamento',
}
const SUGGESTIONS = [
  'Quero cortar o cabelo amanhã à tarde',
  'Tem massagem relaxante no sábado de manhã?',
  'Preciso de uma avaliação na clínica na próxima semana',
]

const messages = ref<ChatMessage[]>([])
const draft = ref('')
const thinking = ref(false)
const error = ref('')
const list = ref<HTMLElement>()

// Na tela, cada chamada de ferramenta vira um passo; o resto são as falas.
const items = computed(() =>
  messages.value.flatMap((m) => {
    if (m.tool_calls)
      return m.tool_calls.map((c) => ({
        kind: 'step',
        text: STEPS[c.function.name] ?? c.function.name,
      }))
    if (m.role === 'tool' || !m.content) return []
    return [{ kind: m.role, text: m.content }]
  }),
)

// Só o markdown que o modelo costuma usar, links e negrito, sem passar HTML para a página.
function parts(text: string) {
  return text
    .split(/(\[[^\]]+\]\(https?:\/\/[^)\s]+\)|https?:\/\/[^\s)\]]+|\*\*[^*]+\*\*)/)
    .map((part, i) => {
      if (i % 2 === 0) return { text: part }
      const link = part.match(/^\[([^\]]+)\]\((.+)\)$/)
      if (link) return { text: link[1], href: link[2] }
      if (part.startsWith('**')) return { text: part.slice(2, -2), bold: true }
      return { text: part, href: part }
    })
}

async function send(text = draft.value) {
  if (!text.trim() || thinking.value) return
  messages.value.push({ role: 'user', content: text.trim() })
  draft.value = ''
  error.value = ''
  thinking.value = true
  await scroll()
  try {
    messages.value = (await api.chat(messages.value)).messages
  } catch (e) {
    messages.value.pop()
    draft.value = text
    error.value = e instanceof ApiError ? e.message : 'O assistente está indisponível no momento'
  } finally {
    thinking.value = false
    await scroll()
  }
}

async function scroll() {
  await nextTick()
  list.value?.scrollTo({ top: list.value.scrollHeight, behavior: 'smooth' })
}
</script>

<template>
  <div class="relative">
    <div class="absolute inset-x-0 top-0 h-64 bg-brand-950" />
    <div class="relative mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <header class="mb-8 text-white">
        <p class="inline-flex items-center gap-2 text-sm font-semibold text-amber-300">
          <BotMessageSquare class="size-4" /> Assistente
        </p>
        <h1 class="mt-2 text-3xl font-extrabold tracking-tight">Agende conversando</h1>
        <p class="mt-2 text-white/70">
          Diga o que você precisa e quando: o assistente procura os horários e agenda para você.
        </p>
      </header>

      <section
        class="flex h-[36rem] flex-col overflow-hidden rounded-3xl bg-white shadow-2xl shadow-brand-900/10 ring-1 ring-ink/5"
      >
        <div ref="list" class="flex-1 space-y-3 overflow-y-auto p-6">
          <div v-if="!items.length" class="grid h-full place-items-center text-center">
            <div>
              <span
                class="mx-auto grid size-14 place-items-center rounded-2xl bg-brand-50 text-brand-700"
              >
                <BotMessageSquare class="size-7" />
              </span>
              <p class="mt-4 font-semibold">Como posso ajudar?</p>
              <div class="mt-5 flex flex-wrap justify-center gap-2">
                <button
                  v-for="suggestion in SUGGESTIONS"
                  :key="suggestion"
                  type="button"
                  class="rounded-full bg-canvas px-4 py-2 text-sm font-medium text-ink/70 ring-1 ring-ink/10 transition hover:bg-brand-50 hover:text-brand-700"
                  @click="send(suggestion)"
                >
                  {{ suggestion }}
                </button>
              </div>
            </div>
          </div>

          <template v-for="(item, i) in items" :key="i">
            <p
              v-if="item.kind === 'step'"
              class="flex items-center gap-2 pl-1 text-xs font-semibold text-ink/40"
            >
              <Wrench class="size-3.5" /> {{ item.text }}
            </p>
            <div
              v-else
              :class="item.kind === 'user' ? 'justify-end' : 'justify-start'"
              class="flex"
            >
              <p
                :class="
                  item.kind === 'user'
                    ? 'rounded-br-md bg-brand-700 text-white'
                    : 'rounded-bl-md bg-canvas text-ink ring-1 ring-ink/5'
                "
                class="max-w-[85%] rounded-2xl px-4 py-2.5 whitespace-pre-line"
              >
                <template v-for="(part, j) in parts(item.text)" :key="j">
                  <a
                    v-if="part.href"
                    :href="part.href"
                    target="_blank"
                    rel="noopener"
                    class="font-semibold break-all text-brand-700 underline underline-offset-2"
                    >{{ part.text }}</a
                  >
                  <strong v-else-if="part.bold" class="font-bold">{{ part.text }}</strong>
                  <template v-else>{{ part.text }}</template>
                </template>
              </p>
            </div>
          </template>

          <div v-if="thinking" class="flex gap-1.5 pl-2" aria-label="Pensando">
            <span
              v-for="d in 3"
              :key="d"
              :style="{ animationDelay: `${d * 150}ms` }"
              class="size-2 animate-bounce rounded-full bg-brand-400"
            />
          </div>
        </div>

        <p
          v-if="error"
          class="mx-6 mb-3 rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700"
        >
          {{ error }}
        </p>
        <form class="flex items-center gap-3 border-t border-ink/5 p-4" @submit.prevent="send()">
          <label class="flex-1">
            <span class="sr-only">Mensagem para o assistente</span>
            <input
              v-model="draft"
              type="text"
              placeholder="Ex.: quero cortar o cabelo na terça às 15h"
              class="w-full rounded-full bg-canvas px-5 py-3 ring-1 ring-ink/10 outline-none focus:ring-2 focus:ring-brand-500"
            />
          </label>
          <button
            type="submit"
            :disabled="thinking || !draft.trim()"
            aria-label="Enviar"
            class="grid size-12 place-items-center rounded-full bg-amber-400 text-brand-950 shadow-lg shadow-amber-500/25 transition hover:bg-amber-300 disabled:opacity-50"
          >
            <SendHorizontal class="size-5" />
          </button>
        </form>
      </section>
      <p class="mt-4 text-center text-xs text-ink/40">
        Roda num modelo local (Ollama) que usa as ferramentas do servidor MCP do VagaCerta.
      </p>
    </div>
  </div>
</template>
