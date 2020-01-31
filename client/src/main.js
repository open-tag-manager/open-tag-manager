// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue'
import App from './App'
import BootstrapVue from 'bootstrap-vue'
import Vuelidate from 'vuelidate'
import VueToasted from 'vue-toasted'
import router from './router'
import storeGenerator from './store'
import plugins from './plugins'
import Amplify from 'aws-amplify'
import {components} from 'aws-amplify-vue'

import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'
import 'flatpickr/dist/flatpickr.css'

import { library } from '@fortawesome/fontawesome-svg-core'
import { faExpand, faCog, faUser, faBuilding, faExclamationTriangle } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

Vue.config.productionTip = false

let apiBase = process.env.API_BASE_URL
if (apiBase.match('/$')) {
  apiBase = apiBase.substr(0, apiBase.length - 1)
}

Amplify.configure({
  Auth: {
    identityPoolId: process.env.COGNITO_IDENTITY_POOL_ID,
    region: process.env.COGNITO_REGION,
    identityPoolRegion: process.env.COGNITO_IDENTITY_POOL_REGION,
    userPoolId: process.env.COGNITO_USER_POOL_ID,
    userPoolWebClientId: process.env.COGNITO_USER_POOL_WEB_CLIENT_ID,
    cookieStorage: {
      domain: process.env.COGNITO_COOKIE_STORAGE_DOMAIN,
      secure: process.env.COGNITO_COOKIE_SECURE === '1'
    }
  },
  API: {
    endpoints: [
      {
        name: 'OTMClientAPI',
        endpoint: apiBase,
        custom_header: async () => {
          return { Authorization: (await Amplify.Auth.currentSession()).idToken.jwtToken }
        }
      }
    ]
  }
})

Vue.use(Vuelidate)
Vue.use(BootstrapVue)
Vue.use(VueToasted)

library.add(faExpand, faCog, faUser, faBuilding, faExclamationTriangle)
Vue.component('fa-icon', FontAwesomeIcon)

const store = storeGenerator(plugins)

const MyComponent = Vue.extend({
  store,
  router: router(store, plugins),
  components: {App, components},
  template: '<App/>'
})

const app = new MyComponent()

store.app = app

for (const plugin of plugins) {
  if (plugin.app) {
    plugin.app(app)
  }
}

app.$mount('#app')
