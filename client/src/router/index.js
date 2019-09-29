import Vue from 'vue'
import Router from 'vue-router'

import Top from '@/pages/Top'
import Auth from '@/pages/Auth'
import Org from '@/pages/Org'
import NoOrgError from '@/pages/NoOrgError'
import Containers from '@/pages/Containers'
import Container from '@/pages/Container'
import ContainerSetting from '@/pages/ContainerSetting'
import ContainerStat from '@/pages/ContainerStat'
import ContainerStatGraph from '@/pages/ContainerStatGraph'
import ContainerGoals from '@/pages/ContainerGoals'
import OrgSettings from '@/pages/OrgSettings'
import OrgSettingsContainers from '@/pages/OrgSettingsContainers'

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
    if (store.state.user.orgs.length > 0) {
      router.push(`/orgs/${store.state.user.orgs[0].org}/containers`)
    } else {
      router.push('/noorg')
    }
  }
})

const router = new Router({
  routes: [
    {
      path: '/',
      name: 'Top',
      component: Top,
      meta: {anonymous: true}
    },
    {
      path: '/login',
      name: 'Auth',
      component: Auth,
      meta: {anonymous: true}
    },
    {
      path: '/noorg',
      name: 'NoOrg',
      component: NoOrgError,
      meta: {secret: true}
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
              component: ContainerStat
            },
            {
              path: 'stat/:statid',
              name: 'Container-Stat-Graph',
              component: ContainerStatGraph
            },
            {
              path: 'goals',
              name: 'Container-Goals',
              component: ContainerGoals
            }
          ]
        },
        {
          path: 'settings',
          name: 'Org-Settings',
          component: OrgSettings,
          children: [
            {
              path: 'containers',
              name: 'Org-Settings-Containers',
              component: OrgSettingsContainers
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
    if (store.state.user.orgs.length > 0) {
      return next(`/orgs/${store.state.user.orgs[0].org}/containers`)
    } else {
      return next('/noorg')
    }
  }
  if (to.meta.secret && !isAuthenticated) {
    return next('/login')
  }

  if (window.OTM) {
    window.OTM.notify('router-before')
  }

  next()
})

router.afterEach(() => {
  if (window.OTM) {
    window.OTM.notify('router-before')
  }
})

export default router
