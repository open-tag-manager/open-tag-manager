<template>
  <div>
    <h2 class="mb-2">Page Table</h2>

    <div v-if="isLoading || !tableData">
      <b-spinner label="Loading..." variant="primary"/> Loading...
    </div>
    <div class="table-container" v-else>
      <div v-if="lineChartFilterUrl">
        Filtered by: {{lineChartFilterUrl}} <a href="#" @click="lineChartFilterUrl = null">x</a>
      </div>
      <stat-line-chart :data="tableData" :filtered-url="lineChartFilterUrl"></stat-line-chart>
      <b-card title="Display References" class="mb-2" >
        <b-card-body>
          <div v-if="!config.domains || config.domains.length === 0">
            <b-link :to="{name: 'Container-Setting'}">Set domains configuration</b-link> to display reference information.
          </div>
          <b-form-radio-group v-model="refererConfig" :disabled="!config.domains || config.domains.length === 0" @input="summarize">
            <b-form-radio :value="null">Hide</b-form-radio>
            <b-form-radio value="url">Show referer URL</b-form-radio>
            <b-form-radio value="domain">Show referer domain</b-form-radio>
          </b-form-radio-group>
        </b-card-body>
      </b-card>
      <b-card title="Metrics" class="mb-2">
        <b-card-body>
          <b-form-checkbox-group v-model="selectedMetrics">
            <b-form-checkbox value="count">PV</b-form-checkbox>
            <b-form-checkbox value="session_count">Session</b-form-checkbox>
            <b-form-checkbox value="user_count">User</b-form-checkbox>
            <b-form-checkbox value="event_count">Event</b-form-checkbox>
            <b-form-checkbox value="w_click_count">Widget Click</b-form-checkbox>
            <b-form-checkbox value="t_click_count">Trivial Click</b-form-checkbox>
            <b-form-checkbox value="avg_scroll_y">Scroll(AVG)</b-form-checkbox>
            <b-form-checkbox value="avg_plt">FP(AVG)</b-form-checkbox>
            <b-form-checkbox value="max_plt">FP(MAX)</b-form-checkbox>
          </b-form-checkbox-group>
        </b-card-body>
      </b-card>
      <stat-table :data="summaryTableData" :metrics-filter="selectedMetrics"
                  :referer-config="refererConfig"
                  @clickGraphUrl="goToUrlGraph"
                  @clickFilterUrl="filterLineChartUrl"
                  @clickShowEvent="goToEventTableWithUrl" />
    </div>
  </div>
</template>

<script>
  import _ from 'lodash'
  import urlParser from 'url'
  import axios from 'axios'
  import {convertUrlForTableData} from '../lib/GraphUril'
  import StatTable from '../components/StatTable'
  import StatLineChart from '../components/StatLineChart'

  export default {
    components: {StatTable, StatLineChart},
    data () {
      return {
        config: null,
        tableData: null,
        summaryTableData: null,
        lineChartFilterUrl: null,
        isLoading: false,
        selectedMetrics: ['count', 'session_count', 'user_count', 'event_count'],
        refererConfig: null
      }
    },
    computed: {
      swaggerDoc () {
        return this.$store.state.container.swaggerDoc
      }
    },
    async mounted () {
      await this.loadData()
    },
    methods: {
      summarize () {
        this.summaryTableData = _(this.tableData).groupBy((d) => {
          let ref = null
          if (this.refererConfig === null) {
            return d.url
          } else if (this.refererConfig === 'url') {
            if (d.p_url === null) {
              ref = 'direct'
            } else {
              if (!this.config.domains.includes(urlParser.parse(d.p_url)['host'])) {
                ref = d.p_url
              }
            }
          } else if (this.refererConfig === 'domain') {
            if (d.p_url === null) {
              ref = 'direct'
            } else {
              const host = urlParser.parse(d.p_url)['host']
              if (!this.config.domains.includes(host)) {
                ref = host
              }
            }
          }
          return `${d.url}_____${ref}`
        }).map((d) => {
          const scrollCount = _.sumBy(d, 's_count')
          const pltCount = _.sumBy(d, 'plt_count')
          const data = {
            count: _.sumBy(d, 'count'),
            session_count: _.sumBy(d, 'session_count'),
            user_count: _.sumBy(d, 'user_count'),
            event_count: _.sumBy(d, 'event_count'),
            t_click_count: _.sumBy(d, 't_click_count'),
            w_click_count: _.sumBy(d, 'w_click_count'),
            avg_scroll_y: null,
            max_scroll_y: null,
            avg_plt: null,
            max_plt: null
          }
          data.url = d[0].url
          let ref = null
          if (this.refererConfig === null) {
          } else if (this.refererConfig === 'url') {
            if (d[0].p_url === null) {
              ref = 'direct'
            } else {
              if (!this.config.domains.includes(urlParser.parse(d[0].p_url)['host'])) {
                ref = d[0].p_url
              }
            }
          } else if (this.refererConfig === 'domain') {
            if (d[0].p_url === null) {
              ref = 'direct'
            } else {
              const host = urlParser.parse(d[0].p_url)['host']
              if (!this.config.domains.includes(host)) {
                ref = host
              }
            }
          }
          data.p_url = ref
          if (scrollCount > 0) {
            data.avg_scroll_y = _.reduce(d, (result, o) => {
              if (!o.s_count) {
                return result
              }
              result += o.avg_scroll_y * o.s_count
              return result
            }, 0) / scrollCount
            data.max_scroll_y = _.maxBy(d, 'max_scroll_y').max_scroll_y
          }
          if (pltCount > 0) {
            data.avg_plt = _.reduce(d, (result, o) => {
              if (!o.plt_count) {
                return result
              }
              result += o.avg_plt * o.plt_count
              return result
            }, 0) / pltCount
            data.max_plt = _.maxBy(d, 'max_plt').max_plt
          }
          return data
        }).value()
      },
      async loadData () {
        this.isLoading = true
        await this.$store.dispatch('container/fetchContainer', {container: this.$route.params.name, org: this.$route.params.org})
        this.config = this.$store.state.container.container
        const stat = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.$route.params.name}/stats/${this.$route.params.statid}`)
        const data = await axios.get(stat.file_url)
        this.tableData = convertUrlForTableData(data.data.table, this.swaggerDoc)
        this.summarize()
        this.isLoading = false
      },
      goToUrlGraph (url) {
        this.$router.push({name: 'Container-Stats-StatId-URLGraph-URL', params: {...this.$router.params, url}})
      },
      filterLineChartUrl (url) {
        this.lineChartFilterUrl = url
      },
      goToEventTableWithUrl (url) {
        this.$router.push({name: 'Container-Stats-StatId-Events', query: {url}})
      }
    }
  }
</script>
