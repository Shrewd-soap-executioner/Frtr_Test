import { createRouter, createWebHistory } from 'vue-router'
import Login from './Pages/Login.vue'
import Register from './Pages/Register.vue'
import Profile from './Pages/Profile.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: '/profile', component: Profile }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router