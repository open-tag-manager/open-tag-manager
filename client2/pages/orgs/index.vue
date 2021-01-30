<template>
  <v-container>
    <h1 class="mb-4 text-center">Organizations</h1>
    <v-list v-if="orgs && orgs.length" outlined class="org-list mx-auto">
      <v-list-item
        v-for="org in orgs"
        :key="org.org"
        :to="{ name: 'orgs-name', params: { name: org.org } }"
      >
        <v-list-item-title>{{ org.org }}</v-list-item-title>
        <code v-if="org.roles.includes('admin')">Admin</code>
        <code v-else-if="org.roles.includes('write')">User</code>
        <code v-else>Read only</code>
      </v-list-item>
    </v-list>
    <div v-else class="text-center">There is no org</div>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'
import { IUserOrgRole } from '~/utils/api/user'
import { session } from '~/store'

@Component({ middleware: 'authenticated' })
export default class OrgsIndex extends Vue {
  get orgs(): IUserOrgRole[] | undefined {
    return session.otmUser?.orgs
  }
}
</script>

<style scoped lang="scss">
.org-list {
  max-width: 400px;
}
</style>
