import _ from 'lodash'

const getters = {
  isAuthenticated (state) {
    return !!state.user
  },
  hasRootRole (state) {
    const root = _.find(state.user.orgs, {org: 'root'})
    return root && root.roles.includes('admin')
  }
}

const state = {
  user: null,
  orgs: [],
  currentOrg: null
}

const mutations = {
  SET_USER (state, {user}) {
    state.user = user
    if (state.user === null) {
      state.orgs = null
      state.currentOrg = null
    } else {
      state.orgs = user.orgs
      state.currentOrg = _.first(state.orgs)
    }
  },
  SET_CURRENT_ORG (state, org) {
    state.currentOrg = org
  }
}

const actions = {
  setUser (ctx, {user}) {
    ctx.commit('SET_USER', {user})
  },
  unsetUser (ctx) {
    ctx.commit('SET_USER', {user: null})
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
