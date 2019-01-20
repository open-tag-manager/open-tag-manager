import _ from 'lodash'

const getters = {
  isAuthenticated (state) {
    return !!state.user
  }
}

const state = {
  user: null,
  orgs: [],
  currentOrg: null
}

const mutations = {
  SET_USER (state, {user, orgs}) {
    state.user = user
    state.orgs = orgs
    state.currentOrg = _.first(state.orgs)
  },
  SET_CURRENT_ORG (state, org) {
    state.currentOrg = org
  }
}

const actions = {
  setUser (ctx, {user, orgs}) {
    ctx.commit('SET_USER', {user, orgs})
  },
  unsetUser (ctx) {
    ctx.commit('SET_USER', {user: null, orgs: []})
    ctx.commit('SET_CURRENT_ORG', null)
  },
  async signOut (ctx) {
    await this.app.$Amplify.Auth.signOut()
    ctx.dispatch('unsetUser')
  },
  setCurrentOrg (ctx, org) {
    ctx.commit('SET_CURRENT_ORG', org)
  }
}

export default {
  state,
  getters,
  actions,
  mutations,
  namespaced: true
}
