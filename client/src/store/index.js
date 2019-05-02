import Vue from 'vue'
import Vuex from 'vuex'

import user from './user'
import container from './container'

Vue.use(Vuex)

export default new Vuex.Store({
  modules: {user, container}
})
