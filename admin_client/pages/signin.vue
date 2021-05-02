<template>
  <v-container fluid>
    <amplify-authenticator>
      <amplify-sign-in slot="sign-in" header-text="Sign in" hide-sign-up />
    </amplify-authenticator>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import { onAuthUIStateChange } from '@aws-amplify/ui-components'
import { session } from '~/store'

@Component
export default class SignIn extends Vue {
  onChange: (() => void) | undefined

  created() {
    this.onChange = onAuthUIStateChange(async (authState, authData) => {
      if (authState === 'signedin' && authData) {
        await session.init()
        await this.$router.push('/')
      }
    })
  }

  beforeDestroy() {
    this.onChange?.()
  }
}
</script>
