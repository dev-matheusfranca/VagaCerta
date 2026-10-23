import { Leaf, Scissors, Sparkles, Stethoscope, Store } from 'lucide-vue-next'

const CATEGORIES = {
  barbearia: { label: 'Barbearia', icon: Scissors, tone: 'from-slate-600 to-slate-900' },
  beleza: { label: 'Beleza', icon: Sparkles, tone: 'from-rose-400 to-fuchsia-600' },
  saude: { label: 'Saúde', icon: Stethoscope, tone: 'from-sky-400 to-brand-700' },
  'bem-estar': { label: 'Bem-estar', icon: Leaf, tone: 'from-brand-400 to-emerald-700' },
}

export function category(key: string) {
  return (
    CATEGORIES[key as keyof typeof CATEGORIES] ?? {
      label: key,
      icon: Store,
      tone: 'from-brand-500 to-brand-800',
    }
  )
}

export function price(cents: number) {
  if (cents === 0) return 'Grátis'
  return (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

export function time(iso: string, timeZone: string) {
  return new Date(iso).toLocaleTimeString('pt-BR', { timeZone, hour: '2-digit', minute: '2-digit' })
}

export function longDate(iso: string, timeZone: string) {
  return new Date(iso).toLocaleDateString('pt-BR', {
    timeZone,
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
}

export function initials(name: string) {
  return name
    .replace(/^Dra?\.\s/, '')
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
}
