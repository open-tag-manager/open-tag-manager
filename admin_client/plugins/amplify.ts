import Amplify, { Hub } from '@aws-amplify/core'
import Auth from '@aws-amplify/auth'
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
        endpoint: process.env.apiBaseUrl!.replace(/\/$/, ''),
        custom_header: async () => {
          return {
            Authorization: `Bearer ${(await Auth.currentSession())
              .getIdToken()
              .getJwtToken()}`,
          }
        },
      },
    ],
  },
})
