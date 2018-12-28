import Vue from 'vue'
import Router from 'vue-router'
import VueCookie from 'vue-cookie'

import Top from '@/pages/Top'
import Login from '@/pages/Login'
import Containers from '@/pages/Containers'
import Container from '@/pages/Container'
import ContainerSetting from '@/pages/ContainerSetting'
import ContainerHome from '@/pages/ContainerHome'
import ContainerStat from '@/pages/ContainerStat'
import ContainerStatGraph from '@/pages/ContainerStatGraph'

import store from '../store'

Vue.use(Router)

const router = new Router({
  routes: [
    {
      path: '/',
      name: 'Top',
      component: Top
    },
    {
      path: '/login',
      name: 'Login',
      component: Login,
      meta: {
        anonymous: true
      }
    },
    {
      path: '/containers',
      name: 'Containers',
      component: Containers,
      meta: {
        secret: true
      }
    },
    {
      path: '/containers/:name',
      name: 'Container',
      component: Container,
      meta: {
        secret: true
      },
      children: [
        {
          path: '',
          name: 'Container-Home',
          component: ContainerHome
        },
        {
          path: 'setting',
          name: 'Container-Setting',
          component: ContainerSetting
        },
        {
          path: 'stat',
          name: 'Container-Stat',
          component: ContainerStat,
          children: [
            {
              path: ':statid',
              name: 'Container-Stat-Graph',
              component: ContainerStatGraph
            }
          ]
        }
      ]
    }
  ]
})

let initialized = false

router.beforeEach(async (to, from, next) => {
  if (!initialized) {
    const token = VueCookie.get('otm_token')
    if (token) {
      try {
        await store.dispatch('user/loginByToken', {token})
      } catch (e) {
        store.dispatch('user/logout')
        return next('/')
      }
    }
    initialized = true
  }

  const isAuthenticated = store.getters['user/isAuthenticated']
  if (to.meta.anonymous && isAuthenticated) {
    return next('/')
  }
  if (to.meta.secret && !isAuthenticated) {
    return next('/login')
  }
  next()
})

export default router
