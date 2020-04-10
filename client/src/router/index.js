import Vue from 'vue'
import Router from 'vue-router'

import Top from '@/pages/Top'
import Auth from '@/pages/Auth'
import Org from '@/pages/Org'
import NoOrgError from '@/pages/NoOrgError'
import Containers from '@/pages/Containers'
import Container from '@/pages/Container'
import ContainerSetting from '@/pages/ContainerSetting'
import ContainerStats from '@/pages/ContainerStats'
import ContainerStatsStatId from '@/pages/ContainerStatsStatId'
import ContainerStatsStatIdPageTable from '@/pages/ContainerStatsStatIdPageTable'
import ContainerStatsStatIdEventTable from '@/pages/ContainerStatsStatIdEventTable'
import ContainerStatsStatIdURLGraph from '@/pages/ContainerStatsStatIdURLGraph'
import ContainerStatsStatIdURLGraphURL from '@/pages/ContainerStatsStatIdURLGraphURL'
import ContainerStatsStatIdURLTree from '@/pages/ContainerStatsStatIdURLTree'
import OrgSettings from '@/pages/OrgSettings'
import OrgSettingsContainers from '@/pages/OrgSettingsContainers'

import * as AmplifyModules from 'aws-amplify'
import {AmplifyPlugin, AmplifyEventBus} from 'aws-amplify-vue'

Vue.use(Router)
Vue.use(AmplifyPlugin, AmplifyModules)

export default (store, plugins) => {
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

  const options = {
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
                path: 'stats',
                name: 'Container-Stats',
                component: ContainerStats
              },
              {
                path: 'stats/:statid',
                name: 'Container-Stats-StatId',
                component: ContainerStatsStatId,
                children: [
                  {
                    path: 'pages',
                    name: 'Container-Stats-StatId-Pages',
                    component: ContainerStatsStatIdPageTable
                  },
                  {
                    path: 'events',
                    name: 'Container-Stats-StatId-Events',
                    component: ContainerStatsStatIdEventTable
                  },
                  {
                    path: 'urlgraph',
                    name: 'Container-Stats-StatId-URLGraph',
                    component: ContainerStatsStatIdURLGraph
                  },
                  {
                    path: 'urltree',
                    name: 'Container-Stats-StatId-URLTree',
                    component: ContainerStatsStatIdURLTree
                  },
                  {
                    path: 'urlgraph/:url',
                    name: 'Container-Stats-StatId-URLGraph-URL',
                    component: ContainerStatsStatIdURLGraphURL
                  }
                ]
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
  }

  for (const plugin of plugins) {
    if (plugin.router) {
      plugin.router(options)
    }
  }

  const router = new Router(options)

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

  return router
}
