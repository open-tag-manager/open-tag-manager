<template>
  <v-container>
    <h1 class="mb-4 text-center">{{ currentOrg }}</h1>
    <v-list v-if="containers" class="container-items mx-auto mb-4" outlined>
      <v-list-item
        v-for="container in containers"
        :key="container.tid"
        :to="{
          name: 'orgs-name-containers-container-edit',
          params: { name: currentOrg, container: container.tid },
        }"
      >
        <v-list-item-title>{{ container.label }}</v-list-item-title>
        <code class="tid">{{ container.tid }}</code>
      </v-list-item>
    </v-list>

    <div class="text-center">
      <v-btn
        class="text-capitalize"
        :to="{ name: 'orgs-name-containers-new', params: { name: currentOrg } }"
      >
        <v-icon left>mdi-plus</v-icon>Add new container
      </v-btn>
      <v-btn
        class="text-capitalize"
        :to="{ name: 'orgs-name-setting', params: { name: currentOrg } }"
      >
        <v-icon left>mdi-cog</v-icon>Setting
      </v-btn>
    </div>
  </v-container>
</template>

<script lang="ts">
import API from '@aws-amplify/api'
import { Component } from 'nuxt-property-decorator'
import { PaginationItem } from '~/utils/api/paginationItem'
import { IContainer } from '~/utils/api/container'
import Org from '~/components/Org'

@Component
export default class OrgsName extends Org {
  containers: IContainer[] | null = null

  head() {
    return {
      title: `${this.currentOrg}'s Containers`,
    }
  }

  async created() {
    const response: PaginationItem<IContainer> = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers`,
      {}
    )
    this.containers = response.items
  }
}
</script>

<style scoped lang="scss">
.container-items {
  max-width: 400px;

  .tid {
    white-space: nowrap;
  }
}
</style>
