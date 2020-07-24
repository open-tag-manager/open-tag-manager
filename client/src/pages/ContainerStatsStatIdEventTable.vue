<template>
  <div>
    <h2 class="mb-2">Event Table</h2>
    <div v-if="isLoading || !eventTableData">
      <b-spinner label="Loading..." variant="primary"/> Loading...
    </div>
    <div v-else>
      <div v-if="eventTableFilterState">
        Filtered by: {{eventTableFilterState}} <a href="#" @click="eventTableFilterState = null">x</a>
      </div>
      <div v-if="eventTableFilterUrl">
        Filtered by: {{eventTableFilterUrl}} <a href="#" @click="eventTableFilterUrl = null">x</a>
      </div>
      <b-form-group label="Enabled Statuses" class="status-filter" v-else>
        <b-form-checkbox-group id="enabled-statuses-event" v-model="enabledStatues"
                               :options="statuses"></b-form-checkbox-group>
      </b-form-group>

      <event-table :data="eventTableData" :filter-state="eventTableFilterState" :filter-states="enabledStatues" :filter-url="eventTableFilterUrl" />
    </div>
  </div>
</template>

<script>
  import _ from 'lodash'
  import EventTable from '../components/EventTable'
  import {convertUrlForTableData} from '../lib/GraphUril'

  const statusPatterns = {
    pageview: /^pageview$/,
    click_widget: /^click_widget.+/,
    click_trivial: /^click_trivial.+/,
    touchstart: /^touchstart_.+/,
    'change-url': /^change-url.+/,
    timer: /^timer_.+/,
    scroll: /^scroll_.+/
  }

  export default {
    components: {EventTable},
    data () {
      return {
        isLoading: false,
        rawEventTableData: null,
        eventTableData: null,
        eventTableFilterState: this.$route.query.state,
        eventTableFilterUrl: this.$route.query.url,
        statuses: _.keys(statusPatterns),
        enabledStatues: _.difference(_.keys(statusPatterns), ['click_trivial', 'timer', 'scroll'])
      }
    },
    computed: {
      swaggerDoc () {
        return this.$store.state.container.swaggerDoc
      }
    },
    async mounted () {
      this.eventTableFilterUrl = this.$route.query.url
      await this.loadData()
    },
    methods: {
      async loadData () {
        this.isLoading = true
        const statId = this.$route.params.statid
        const data = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.$route.params.name}/stats/${encodeURIComponent(statId)}/events`)
        this.rawEventTableData = data

        if (!this.rawEventTableData) {
          this.isLoading = false
          return null
        }

        let eventTableData = convertUrlForTableData(this.rawEventTableData.event_table, this.swaggerDoc)
        eventTableData = _(eventTableData).groupBy((d) => {
          return `${d.url}-${d.state}`
        }).map((d) => {
          const data = d[0]
          data['count'] = _.sumBy(d, 'count')
          return data
        }).value()
        this.eventTableData = eventTableData

        this.isLoading = false
      }
    }
  }
</script>
