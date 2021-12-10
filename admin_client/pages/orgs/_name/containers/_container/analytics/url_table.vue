<template>
  <v-container class="url-table">
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
    <stat-line-chart v-if="!isLoading" :data="pageviewTimeSeries" />
    <v-data-table :headers="headers" :items="table" :loading="isLoading">
    </v-data-table>
  </v-container>
</template>

<script lang="ts">
import { Component, Watch } from 'vue-property-decorator'
import {
  format as dateFormat,
  parse as dateParse,
  sub as dateSub,
} from 'date-fns'
import { IContainer } from '~/utils/api/container'
import { IStatDataTable, IStatPageviewTimeSeriesTable } from '~/utils/api/stat'
import StatLineChart from '~/components/StatLineChart.vue'
import OrgContainer from '~/components/OrgContainer'
import { pageviewTimeSeriesQuery, urlTableQuery } from '~/utils/query'
@Component({
  components: { StatLineChart },
})
export default class UrlTable extends OrgContainer {
  isLoading: boolean = false

  datepickerModal: boolean = false

  container?: IContainer
  table: IStatDataTable[] = []
  pageviewTimeSeries: IStatPageviewTimeSeriesTable[] = []

  date: string[] = [
    dateFormat(dateSub(new Date(), { weeks: 1 }), 'yyyy-MM-dd'),
    dateFormat(new Date(), 'yyyy-MM-dd'),
  ]

  get formattedDate(): string {
    if (this.date && this.date.length > 1) {
      const date = [...this.date].sort()
      return `${date[0]}〜${date[1]}`
    }

    return ''
  }

  get headers(): object[] {
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

    const date = [...this.date].sort()
    const result = await urlTableQuery(
      this.currentOrg,
      this.currentContainer,
      dateParse(date[0], 'yyyy-MM-dd', new Date()).getTime(),
      dateParse(date[1], 'yyyy-MM-dd', new Date()).getTime()
    )
    this.table = result.table

    const pageviewSeries = await pageviewTimeSeriesQuery(
      this.currentOrg,
      this.currentContainer,
      dateParse(date[0], 'yyyy-MM-dd', new Date()).getTime(),
      dateParse(date[1], 'yyyy-MM-dd', new Date()).getTime()
    )
    this.pageviewTimeSeries = pageviewSeries.table

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
.url-table {
  .datepicker {
    max-width: 290px;
  }
}
</style>
