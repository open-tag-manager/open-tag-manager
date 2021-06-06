<template>
  <v-app>
    <v-app-bar app clipped-left>
      <v-toolbar-title>
        <nuxt-link to="/">OTM Admin Console</nuxt-link>
      </v-toolbar-title>
      <v-spacer />
      <v-btn v-if="!user" text :to="{ name: 'signin' }">Sign In</v-btn>
      <v-menu v-else bottom left>
        <template #activator="{ on, attrs }">
          <v-btn text v-bind="attrs" v-on="on">{{ user.username }}</v-btn>
        </template>
        <v-list>
          <v-list-item
            v-if="$store.getters['session/hasRootAdminRole']"
            :to="{ name: 'admin-users' }"
            >Admin Setting</v-list-item
          >
          <v-list-item @click="signOut">Sign out</v-list-item>
        </v-list>
      </v-menu>
    </v-app-bar>
    <v-main>
      <nuxt />
    </v-main>
  </v-app>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import { session } from '~/utils/store-accessor'

@Component
export default class DefaultLayout extends Vue {
  async signOut() {
    await session.signOut()
    await this.$router.push('/')
  }

  get user() {
    return session.user
  }
}
</script>
