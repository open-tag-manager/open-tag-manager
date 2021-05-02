<template>
  <v-container fluid class="text-center rounded py-10 grey lighten-3 title">
    <h1 class="mb-4">Open Tag Manager</h1>
    <v-btn v-if="!user" :to="{ name: 'signin' }">Sign in</v-btn>
    <v-list v-else class="menu mx-auto">
      <v-list-item :to="{ name: 'orgs' }">Organizations</v-list-item>
    </v-list>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import { session } from '~/store'

@Component
export default class Index extends Vue {
  get user() {
    return session.user
  }
}
</script>

<style lang="scss" scoped>
.menu {
  max-width: 250px;
}
</style>
