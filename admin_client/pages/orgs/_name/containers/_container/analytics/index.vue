<template>
  <v-container>
    <h1>Analytics</h1>

    <h2>Create new analytics</h2>
    <new-stat-form
      :org-name="currentOrg"
      :container-name="currentContainer"
      @create="load"
    />

    <h2 class="mb-2">View analytics history</h2>
    <v-btn class="mb-2" @click="load">Reload</v-btn>
    <v-progress-linear v-if="isLoading" indeterminate />
    <v-list v-if="stats">
      <v-list-item
        v-for="stat in stats"
        :key="stat.file_key"
        two-line
        :to="statLink(stat)"
      >
        <v-list-item-content>
          <v-list-item-title>
            {{ stat.label || stat.file_key }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ dateFormat(stat) }}
          </v-list-item-subtitle>
        </v-list-item-content>
        <code>{{ stat.status }}</code>
      </v-list-item>
    </v-list>
  </v-container>
</template>

<script lang="ts">
import { Component } from 'vue-property-decorator'
import API from '@aws-amplify/api'
import { format as dateFormat } from 'date-fns'
import OrgContainer from '~/components/OrgContainer'
import NewStatForm from '~/components/NewStatForm.vue'
import { PaginationItem } from '~/utils/api/paginationItem'
import { IStat } from '~/utils/api/stat'

@Component({ components: { NewStatForm } })
export default class Analytics extends OrgContainer {
  isLoading: boolean = false
  stats: IStat[] | null = null

  async load() {
    this.isLoading = true
    const response: PaginationItem<IStat> = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${this.currentContainer}/stats`,
      {}
    )
    this.stats = response.items
    this.isLoading = false
  }

  dateFormat(stat: IStat): string {
    return `${dateFormat(new Date(stat.stime), 'yyyy-MM-dd')}〜${dateFormat(
      new Date(stat.etime),
      'yyyy-MM-dd'
    )}`
  }

  statLink(stat: IStat): object | null {
    if (stat.status === 'COMPLETE') {
      return {
        name: 'orgs-name-containers-container-analytics-stat-url_table',
        params: {
          org: this.currentOrg,
          container: this.currentContainer,
          stat: stat.timestamp,
        },
      }
    }

    return null
  }

  async created() {
    await this.load()
  }
}
</script>
