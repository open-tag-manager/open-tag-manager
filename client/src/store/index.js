import Vue from 'vue'
import Vuex from 'vuex'

import user from './user'
import container from './container'

Vue.use(Vuex)

export default (plugins) => {
  const options = {
    state: {
      containerMenu: [],
      orgMenu: [],
      urlTableAction: [],
      eventTableAction: []
    },
    mutations: {
      addContainerMenu (state, menuData) {
        state.containerMenu = [...state.containerMenu, menuData]
      },
      addOrgMenu (state, menuData) {
        state.orgMenu = [...state.orgMenu, menuData]
      },
      addTableAction (state, action) {
        state.urlTableAction = [...state.urlTableAction, action]
      },
      addEventTableAction (state, action) {
        state.eventTableAction = [...state.eventTableAction, action]
      }
    },
    actions: {
      addContainerMenu ({commit}, menuData) {
        commit('addContainerMenu', menuData)
      },
      addOrgMenu ({commit}, menuData) {
        commit('addOrgMenu', menuData)
      },
      addTableAction ({commit}, action) {
        commit('addTableAction', action)
      },
      addEventTableAction ({commit}, action) {
        commit('addEventTableAction', action)
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
