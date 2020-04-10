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
      <stat-table :data="summaryTableData" @clickGraphUrl="goToUrlGraph"
                  @clickFilterUrl="filterLineChartUrl"
                  @clickShowEvent="goToEventTableWithUrl" />
    </div>
  </div>
</template>

<script>
  import _ from 'lodash'
  import axios from 'axios'
  import {convertUrlForTableData} from '../lib/GraphUril'
  import StatTable from '../components/StatTable'
  import StatLineChart from '../components/StatLineChart'

  export default {
    components: {StatTable, StatLineChart},
    data () {
      return {
        tableData: null,
        summaryTableData: null,
        lineChartFilterUrl: null,
        isLoading: false
      }
    },
    computed: {
      swaggerDoc () {
        return this.$store.state.container.swaggerDoc
      }
    },
    async mounted () {
      await this.$store.dispatch('container/fetchSwaggerDoc', {
        org: this.$route.params.org,
        container: this.$route.params.name
      })
      await this.loadData()
    },
    methods: {
      async loadData () {
        this.isLoading = true
        const stats = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.$route.params.name}/stats`)
        const stat = _.find(stats, {key: this.$route.params.statid})
        const data = await axios.get(stat.url)
        this.tableData = convertUrlForTableData(data.data.table, this.swaggerDoc)
        this.summaryTableData = _(this.tableData).groupBy('url').map((d, url) => {
          const scrollCount = _.sumBy(d, 's_count')
          const pltCount = _.sumBy(d, 'plt_count')
          const data = {
            url,
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
