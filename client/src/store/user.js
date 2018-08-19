import api from '../api'

const getters = {
  isAuthenticated (state) {
    return !!state.user
  }
}

const state = {
  user: null,
  token: null
}

const mutations = {
  SET_USER (state, {user, token}) {
    state.user = user
    state.token = token
  }
}

const actions = {
  async login (ctx, {username, password}) {
    const response = await api(this).post('/login', {username, password})
    const user = response.data
    const token = user.token
    this.app.$cookie.set('otm_token', token, {path: process.env.BASE_PATH})
    ctx.commit('SET_USER', {user, token})
  },
  async loginByToken (ctx, {token}) {
    const response = await api(this, {headers: {Authorization: token}}).get('/')
    const user = response.data
    user.token = token
    ctx.commit('SET_USER', {user, token})
  },
  logout ({commit}) {
    commit('SET_USER', {user: null, token: null})
    this.app.$cookie.delete('otm_token')
  }
}

export default {
  state,
  getters,
  actions,
  mutations,
  namespaced: true
}
