<template>
  <div>
    <v-navigation-drawer app clipped>
      <v-list>
        <v-list-item
          :to="{ name: 'orgs-name', params: { name: currentOrg } }"
          exact
        >
          <v-list-item-icon>
            <v-icon>mdi-arrow-left</v-icon>
          </v-list-item-icon>
          Containers
        </v-list-item>
        <v-divider />
        <v-list-item>
          <v-list-item-icon>
            <v-icon>mdi-account-multiple</v-icon>
          </v-list-item-icon>
          Users
        </v-list-item>
        <v-list-item>
          <v-list-item-icon>
            <v-icon>mdi-chart-bell-curve-cumulative</v-icon>
          </v-list-item-icon>
          Usage
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <nuxt-child />
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'

@Component
export default class OrgsSetting extends Vue {
  get currentOrg(): String {
    return this.$route.params.name
  }
}
</script>
