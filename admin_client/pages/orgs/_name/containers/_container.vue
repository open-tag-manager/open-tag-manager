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

        <v-list-item two-line>
          <v-list-item-content>
            <v-list-item-title>{{ containerLabel }}</v-list-item-title>
            <v-list-item-subtitle>{{ containerTid }}</v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>

        <v-list-item
          :to="{
            name: 'orgs-name-containers-container-analytics',
            params: { name: currentOrg, container: currentContainer },
          }"
        >
          <v-list-item-icon>
            <v-icon>mdi-chart-areaspline</v-icon>
          </v-list-item-icon>
          Analytics
        </v-list-item>

        <v-list-item
          :to="{
            name: 'orgs-name-containers-container-users',
            params: { name: currentOrg, container: currentContainer },
          }"
        >
          <v-list-item-icon>
            <v-icon>mdi-account-group</v-icon>
          </v-list-item-icon>
          Users
        </v-list-item>

        <v-list-item
          :to="{
            name: 'orgs-name-containers-container-goals',
            params: { name: currentOrg, container: currentContainer },
          }"
        >
          <v-list-item-icon>
            <v-icon>mdi-flag</v-icon>
          </v-list-item-icon>
          Goal
        </v-list-item>
        <v-list-item
          :to="{
            name: 'orgs-name-containers-container-edit',
            params: { name: currentOrg, container: currentContainer },
          }"
        >
          <v-list-item-icon>
            <v-icon>mdi-pencil</v-icon>
          </v-list-item-icon>
          Edit
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <nuxt-child />
  </div>
</template>

<script lang="ts">
import { Component } from 'vue-property-decorator'
import API from '@aws-amplify/api'
import OrgContainer from '~/components/OrgContainer'
import { IContainer } from '~/utils/api/container'

@Component
export default class Container extends OrgContainer {
  container: IContainer | null = null

  get containerTid() {
    return this.container?.tid
  }

  get containerLabel() {
    return this.container?.label
  }

  async created() {
    const container: IContainer = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${this.currentContainer}`,
      {}
    )
    this.container = container
  }
}
</script>
