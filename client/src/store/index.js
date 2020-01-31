import Vue from 'vue'
import Vuex from 'vuex'

import user from './user'
import container from './container'

Vue.use(Vuex)

export default (plugins) => {
  const options = {
    modules: {user, container}
  }

  for (const plugin of plugins) {
    if (plugin.store) {
      plugin.store(options)
    }
  }

  return new Vuex.Store(options)
}
