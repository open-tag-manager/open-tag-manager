<template>
  <v-container>
    <v-row>
      <v-checkbox
        v-for="status in statuses"
        :key="status"
        v-model="enabledStatus"
        :label="status"
        :value="status"
        class="mr-4"
      />
    </v-row>

    <v-data-table :headers="headers" :items="tableData" :loading="isLoading" />
  </v-container>
</template>

<script lang="ts">
import { Component } from 'vue-property-decorator'
import { API } from '@aws-amplify/api'
import { groupBy, sumBy } from 'lodash-es'
import OrgContainerStat from '~/components/OrgContainerStat'
import { TableHeader } from '~/utils/api/table_header'
import { IContainer } from '~/utils/api/container'
import { IStatEventData, IStatEventTable } from '~/utils/api/stat'

const statusPatterns: Record<string, RegExp> = {
  pageview: /^pageview$/,
  click_widget: /^click_widget.+/,
  click_trivial: /^click_trivial.+/,
  touchstart: /^touchstart_.+/,
  'change-url': /^change-url.+/,
  timer: /^timer_.+/,
  scroll: /^scroll_.+/,
}

@Component
export default class EventTable extends OrgContainerStat {
  isLoading: boolean = false
  container: IContainer | null = null
  rawTableData: IStatEventData | null = null
  statuses: string[] = Object.keys(statusPatterns)
  enabledStatus: string[] = [
    'pageview',
    'click_widget',
    'touchstart',
    'change-url',
  ]

  get headers(): TableHeader[] {
    return [
      {
        text: 'URL',
        value: 'url',
        sortable: true,
      },
      {
        text: 'Title',
        value: 'title',
        sortable: true,
      },
      {
        text: 'Event',
        value: 'state',
        sortable: true,
      },
      {
        text: 'Label',
        value: 'label',
        sortable: true,
      },
      {
        text: 'Count',
        value: 'count',
        sortable: true,
      },
    ]
  }

  get tableData(): IStatEventTable[] {
    if (!this.rawTableData) {
      return []
    }

    // filter rule
    const filtered = this.rawTableData.event_table.filter((d) => {
      for (const key in statusPatterns) {
        if (this.enabledStatus.includes(key)) {
          if (d.state?.match(statusPatterns[key])) {
            return true
          }
        }
      }

      return false
    })

    const tableData: IStatEventTable[] = []
    const grouped = groupBy(filtered, (d: IStatEventTable) => {
      return `${d.url}-${d.state}`
    })
    for (const key in grouped) {
      const d: IStatEventTable[] = grouped[key]
      const d2: IStatEventTable = { ...d[0] }
      d2.count = sumBy(d, 'count')
      tableData.push(d2)
    }
    return tableData
  }

  async load() {
    this.isLoading = true
    this.container = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${this.currentContainer}`,
      {}
    )
    this.rawTableData = await API.get(
      'OTMClientAPI',
      `/orgs/${this.currentOrg}/containers/${
        this.currentContainer
      }/stats/${encodeURIComponent(this.currentStat)}/events`,
      {}
    )
    this.isLoading = false
  }

  async mounted() {
    await this.load()
  }
}
</script>
