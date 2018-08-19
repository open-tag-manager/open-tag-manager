// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue'
import App from './App'
import BootstrapVue from 'bootstrap-vue'
import VueCookie from 'vue-cookie'
import Vuelidate from 'vuelidate'
import VueToasted from 'vue-toasted'
import store from './store'
import router from './router'

import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'
import 'flatpickr/dist/flatpickr.css'

import { library } from '@fortawesome/fontawesome-svg-core'
import { faExpand } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

Vue.config.productionTip = false
Vue.use(Vuelidate)
Vue.use(BootstrapVue)
Vue.use(VueCookie)
Vue.use(VueToasted)

library.add(faExpand)
Vue.component('fa-icon', FontAwesomeIcon)

router.$store = store

/* eslint-disable no-new */
const vue = new Vue({
  el: '#app',
  store,
  router,
  components: {App},
  template: '<App/>'
})

store.app = vue
