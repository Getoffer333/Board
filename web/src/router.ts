import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import Resumes from './views/Resumes.vue'
import Jds from './views/Jds.vue'
import Applications from './views/Applications.vue'
import Interviews from './views/Interviews.vue'
import Skills from './views/Skills.vue'
import Scripts from './views/Scripts.vue'
import Contacts from './views/Contacts.vue'
import Questions from './views/Questions.vue'
import AiTools from './views/AiTools.vue'
import Settings from './views/Settings.vue'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: Dashboard },
  { path: '/resumes', component: Resumes },
  { path: '/jds', component: Jds },
  { path: '/applications', component: Applications },
  { path: '/interviews', component: Interviews },
  { path: '/scripts', component: Scripts },
  { path: '/skills', component: Skills },
  { path: '/contacts', component: Contacts },
  { path: '/questions', component: Questions },
  { path: '/ai', component: AiTools },
  { path: '/settings', component: Settings }
]

export default createRouter({
  history: createWebHashHistory(),
  routes
})
