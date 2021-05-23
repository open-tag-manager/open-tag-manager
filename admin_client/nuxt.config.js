require('dotenv').config()

export default {
  // Disable server-side rendering (https://go.nuxtjs.dev/ssr-mode)
  ssr: false,

  env: {
    awsRegion: process.env.AWS_DEFAULT_REGION,
    apiBaseUrl: process.env.API_BASE_URL || 'http://localhost:8000',
    cognitoIdentityPoolId: process.env.COGNITO_IDENTITY_POOL_ID,
    cognitoRegion: process.env.COGNITO_REGION || process.env.AWS_DEFAULT_REGION,
    cognitoIdentityPoolRegion:
      process.env.COGNITO_IDENTITY_POOL_REGION ||
      process.env.AWS_DEFAULT_REGION,
    cognitoPoolId: process.env.COGNITO_USER_POOL_ID,
    cognitoPoolWebClientId: process.env.COGNITO_USER_POOL_WEB_CLIENT_ID,
    cognitoCookieStorageDomain:
      process.env.COGNITO_COOKIE_STORAGE_DOMAIN || 'localhost',
    cognitoCookieSecure: process.env.COGNITO_COOKIE_SECURE,
  },

  // Global page headers (https://go.nuxtjs.dev/config-head)
  head: {
    titleTemplate: '%s - OTM Admin Console',
    title: 'OTM Admin Console',
    meta: [
      { charset: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { hid: 'description', name: 'description', content: '' },
    ],
    link: [{ rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }],
  },

  // Global CSS (https://go.nuxtjs.dev/config-css)
  css: [],

  // Plugins to run before rendering page (https://go.nuxtjs.dev/config-plugins)
  plugins: [{ src: '~/plugins/amplify.ts', ssr: false }],

  // Auto import components (https://go.nuxtjs.dev/config-components)
  components: true,

  // Modules for dev and build (recommended) (https://go.nuxtjs.dev/config-modules)
  buildModules: [
    '@nuxtjs/dotenv',
    // https://go.nuxtjs.dev/typescript
    '@nuxt/typescript-build',
    // https://go.nuxtjs.dev/vuetify
    '@nuxtjs/vuetify',
    'nuxt-client-init-module',
  ],

  // Modules (https://go.nuxtjs.dev/config-modules)
  modules: [],

  // Vuetify module configuration (https://go.nuxtjs.dev/config-vuetify)
  vuetify: {
    customVariables: ['~/assets/variables.scss'],
    theme: {},
  },

  // Build Configuration (https://go.nuxtjs.dev/config-build)
  build: {},

  watch: ['~/utils/**/*.ts'],
}
