import Vue from 'vue'
import Vuex from 'vuex'

import user from './user'
import container from './container'

Vue.use(Vuex)

export default (plugins) => {
  const options = {
    state: {
      containerMenu: [],
      orgMenu: []
    },
    mutations: {
      addContainerMenu (state, menuData) {
        state.containerMenu = [...state.containerMenu, menuData]
      },
      addOrgMenu (state, menuData) {
        state.orgMenu = [...state.orgMenu, menuData]
      }
    },
    actions: {
      addContainerMenu ({commit}, menuData) {
        commit('addContainerMenu', menuData)
      },
      addOrgMenu ({commit}, menuData) {
        commit('addOrgMenu', menuData)
      }
    },
    modules: {user, container}
  }

  for (const plugin of plugins) {
    if (plugin.store) {
      plugin.store(options)
    }
  }

  return new Vuex.Store(options)
}
