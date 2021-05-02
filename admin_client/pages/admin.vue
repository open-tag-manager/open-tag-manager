<template>
  <div>
    <v-navigation-drawer app clipped>
      <v-list>
        <v-list-item :to="{ name: 'admin-users' }">
          <v-list-item-icon>
            <v-icon>mdi-account-multiple</v-icon>
          </v-list-item-icon>
          Users
        </v-list-item>
      </v-list>

      <v-list>
        <v-list-item :to="{ name: 'admin-orgs' }">
          <v-list-item-icon>
            <v-icon>mdi-office-building</v-icon>
          </v-list-item-icon>
          Organizations
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <nuxt-child />
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'

@Component({ middleware: 'authenticatedRootAdmin' })
export default class AdminIndex extends Vue {}
</script>
