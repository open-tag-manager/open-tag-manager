import Vue from 'vue'
import Router from 'vue-router'

import Top from '@/pages/Top'
import Auth from '@/pages/Auth'
import Org from '@/pages/Org'
import Containers from '@/pages/Containers'
import Container from '@/pages/Container'
import ContainerSetting from '@/pages/ContainerSetting'
import ContainerStat from '@/pages/ContainerStat'
import ContainerStatGraph from '@/pages/ContainerStatGraph'

import * as AmplifyModules from 'aws-amplify'
import {AmplifyPlugin, AmplifyEventBus} from 'aws-amplify-vue'
import store from '../store'

Vue.use(Router)
Vue.use(AmplifyPlugin, AmplifyModules)

const getUser = async () => {
  let user = null
  try {
    user = await Vue.prototype.$Amplify.Auth.currentAuthenticatedUser()
  } catch (e) {
    return null
  }

  if (user && user.signInUserSession) {
    const orgs = await Vue.prototype.$Amplify.API.get('OTMClientAPI', '/orgs')
    store.dispatch('user/setUser', {user, orgs})
    return user
  } else {
    store.dispatch('user/unsetUser')
    return null
  }
}

AmplifyEventBus.$on('authState', async (state) => {
  if (state === 'signedOut') {
    store.dispatch('user/unsetUser')
    router.push('/')
  } else if (state === 'signedIn') {
    await getUser()
    router.push('/')
  }
})

const router = new Router({
  routes: [
    {
      path: '/',
      name: 'Top',
      component: Top
    },
    {
      path: '/login',
      name: 'Auth',
      component: Auth,
      meta: {anonymous: true}
    },
    {
      path: '/orgs/:org',
      name: 'Org',
      component: Org,
      meta: {secret: true},
      children: [
        {
          path: 'containers',
          name: 'Containers',
          component: Containers
        },
        {
          path: 'containers/:name',
          name: 'Container',
          component: Container,
          children: [
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
    }
  ]
})

let initialized = false

router.beforeEach(async (to, from, next) => {
  if (!initialized) {
    await getUser()
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
