<template>
  <v-container>
    <stat-line-chart v-if="!isLoading" :data="table" />
    <v-data-table :headers="headers" :items="table" :loading="isLoading">
    </v-data-table>
  </v-container>
</template>

<script lang="ts">
import { Component } from 'vue-property-decorator'
import { API } from '@aws-amplify/api'
import OrgContainerStat from '~/components/OrgContainerStat'
import { IContainer } from '~/utils/api/container'
import { IStat, IStatData, IStatDataTable } from '~/utils/api/stat'
import StatLineChart from '~/components/StatLineChart.vue'
@Component({
  components: { StatLineChart },
})
export default class UrlTable extends OrgContainerStat {
  isLoading: boolean = false
  container?: IContainer
  table: IStatDataTable[] = []

  get headers(): object[] {
    return [
      {
        text: 'URL',
        value: 'url',
        sortable: true,
      },
      {
        text: 'Prev URL',
        value: 'p_url',
        sortable: true,
      },
      {
        text: 'Count',
        value: 'count',
        sortable: true,
      },
      {
        text: 'Session Count',
        value: 'session_count',
        sortable: true,
      },
      {
        text: 'User Count',
        value: 'user_count',
        sortable: true,
      },
      {
        text: 'Widget Click',
        value: 'w_click_count',
        sortable: true,
      },
      {
        text: 'Trivial Click',
        value: 't_click_count',
        sortable: true,
      },
      {
        text: 'Scroll(AVG)',
        value: 'avg_scroll_y',
        sortable: true,
      },
      {
        text: 'Scroll(MAX)',
        value: 'max_scroll_y',
        sortable: true,
      },
      {
        text: 'FP(AVG)',
        value: 'avg_plt',
        sortable: true,
      },
      {
        text: 'FP(MAX)',
        value: 'max_plt',
        sortable: true,
      },
    ]
  }

  async load() {
    this.isLoading = true
    this.container = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${this.currentContainer}`,
      {}
    )
    const stat: IStat = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${
        this.currentContainer
      }/stats/${encodeURIComponent(this.currentStat)}`,
      {}
    )
    const response: Response = await fetch(stat.file_url, { method: 'GET' })
    const statData: IStatData = await response.json()
    this.table = statData.table
    this.isLoading = false
  }

  async created() {
    await this.load()
  }
}
</script>
