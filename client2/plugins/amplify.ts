import Vue from 'vue'
import Amplify from '@aws-amplify/core'
import '@aws-amplify/ui-vue'

Amplify.configure({
  aws_project_region: process.env.awsRegion,
  Auth: {
    identityPoolId: process.env.cognitoIdentityPoolId,
    region: process.env.cognitoRegion,
    identityPoolRegion: process.env.cognitoIdentityPoolRegion,
    userPoolId: process.env.cognitoPoolId,
    userPoolWebClientId: process.env.cognitoPoolWebClientId,
    cookieStorage: {
      domain: process.env.cognitoCookieStorageDomain,
      secure: !!process.env.cognitoCookieSecure,
    },
  },
  API: {
    endpoints: [
      {
        name: 'OTMClientAPI',
        endpoint: process.env.apiBaseUrl,
      },
    ],
  },
})

// @ts-ignore
Vue.use(Amplify)
