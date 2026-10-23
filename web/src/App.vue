<script setup lang="ts">
import { CalendarCheck, LayoutDashboard } from 'lucide-vue-next'
</script>

<template>
  <div class="flex min-h-dvh flex-col">
    <header class="sticky top-0 z-30 border-b border-ink/5 bg-white/75 backdrop-blur-lg">
      <div class="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <RouterLink to="/" class="flex items-center gap-2.5">
          <span
            class="grid size-9 place-items-center rounded-xl bg-linear-to-br from-brand-500 to-brand-800 text-white shadow-lg shadow-brand-800/25"
          >
            <CalendarCheck class="size-5" :stroke-width="2.25" />
          </span>
          <span class="text-lg font-extrabold tracking-tight">
            Vaga<span class="text-brand-600">Certa</span>
          </span>
        </RouterLink>
        <nav class="flex items-center gap-1">
          <RouterLink
            :to="{ name: 'home', hash: '#estabelecimentos' }"
            class="hidden rounded-full px-4 py-2 text-sm font-semibold text-ink/70 transition hover:bg-brand-50 hover:text-brand-700 sm:block"
          >
            Estabelecimentos
          </RouterLink>
          <RouterLink
            :to="{ name: 'painel' }"
            class="inline-flex items-center gap-2 rounded-full bg-brand-50 px-4 py-2 text-sm font-semibold text-brand-700 transition hover:bg-brand-100"
          >
            <LayoutDashboard class="size-4" /> Área do estabelecimento
          </RouterLink>
        </nav>
      </div>
    </header>

    <main class="flex-1">
      <RouterView />
    </main>

    <footer class="border-t border-ink/5 py-8 text-center text-sm text-ink/45">
      VagaCerta · microsserviços com FastAPI, PostgreSQL e Vue
    </footer>
  </div>
</template>
