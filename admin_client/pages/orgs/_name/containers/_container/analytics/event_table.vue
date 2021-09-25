<template>
  <v-container class="event-table">
    <div class="ml-auto datepicker">
      <v-dialog
        ref="datepicker"
        v-model="datepickerModal"
        :return-value.sync="date"
        persistent
        width="290px"
      >
        <template v-slot:activator="{ on, attrs }">
          <v-text-field
            v-model="formattedDate"
            label="Date"
            readonly
            v-bind="attrs"
            v-on="on"
          />
        </template>
        <v-date-picker v-model="date" no-title scrollable range :max="maxDate">
          <v-spacer />
          <v-btn text color="primary" @click="datepickerModal = false">
            Cancel
          </v-btn>
          <v-btn
            text
            color="primary"
            @click="
              $refs.datepicker.save(date)
              changeDate()
            "
          >
            OK
          </v-btn>
        </v-date-picker>
      </v-dialog>
    </div>

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
import { Component, Watch } from 'vue-property-decorator'
import { groupBy, sumBy } from 'lodash-es'
import {
  format as dateFormat,
  parse as dateParse,
  sub as dateSub,
} from 'date-fns'
import { TableHeader } from '~/utils/api/table_header'
import { IContainer } from '~/utils/api/container'
import { IStatEventTable, IStatEventTableData } from '~/utils/api/stat'
import OrgContainer from '~/components/OrgContainer'
import { eventTableQuery, msckQuery } from '~/utils/query'

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
export default class EventTable extends OrgContainer {
  isLoading: boolean = false

  datepickerModal: boolean = false
  date: string[] = [
    dateFormat(dateSub(new Date(), { weeks: 1 }), 'yyyy-MM-dd'),
    dateFormat(new Date(), 'yyyy-MM-dd'),
  ]

  container: IContainer | null = null
  rawTableData: IStatEventTableData | null = null
  statuses: string[] = Object.keys(statusPatterns)
  enabledStatus: string[] = [
    'pageview',
    'click_widget',
    'touchstart',
    'change-url',
  ]

  get formattedDate(): string {
    if (this.date && this.date.length > 1) {
      const date = [...this.date].sort()
      return `${date[0]}〜${date[1]}`
    }

    return ''
  }

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
    const filtered = this.rawTableData.table.filter((d) => {
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

    await msckQuery()
    const date = [...this.date].sort()
    const result = await eventTableQuery(
      this.currentOrg,
      this.currentContainer,
      dateParse(date[0], 'yyyy-MM-dd', new Date()).getTime(),
      dateParse(date[1], 'yyyy-MM-dd', new Date()).getTime()
    )
    this.rawTableData = result
    this.isLoading = false
  }

  async changeDate() {
    const date = [...this.date].sort()
    await this.$router.push({ query: { stime: date[0], etime: date[1] } })
  }

  @Watch('$route.query')
  async changeRouteQuery() {
    await this.$fetch()
  }

  async fetch() {
    if (this.$route.query.stime) {
      this.date[0] = this.$route.query.stime as string
    }
    if (this.$route.query.etime) {
      this.date[1] = this.$route.query.etime as string
    }

    await this.load()
  }
}
</script>

<style lang="scss" scoped>
.event-table {
  .datepicker {
    max-width: 290px;
  }
}
</style>
