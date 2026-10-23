import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'
import BookingView from './views/BookingView.vue'
import BusinessView from './views/BusinessView.vue'
import HomeView from './views/HomeView.vue'
import OfferView from './views/OfferView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/estabelecimentos/:id', name: 'business', component: BusinessView, props: true },
    { path: '/agendamentos/:id', name: 'booking', component: BookingView, props: true },
    { path: '/ofertas/:id', name: 'offer', component: OfferView, props: true },
  ],
  scrollBehavior: (to) => (to.hash ? { el: to.hash, behavior: 'smooth' } : { top: 0 }),
})

createApp(App).use(router).mount('#app')
