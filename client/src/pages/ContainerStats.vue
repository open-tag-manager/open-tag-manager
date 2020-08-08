<template>
  <div>
    <div class="container py-2">
      <div v-if="stats">
        <div class="mb-4">
          <h3>Make New Stats</h3>
          <form @submit.prevent="makeReport">
            <div class="d-flex align-items-center">
              <div class="form-group">
                <label for="stime">Report From</label>
                <flat-pickr v-model="stime" class="form-control" id="stime"
                            :config="{enableTime: true, dateFormat: 'Y-m-d H:i'}"></flat-pickr>
              </div>
              <div class="mx-2">〜</div>
              <div class="form-group">
                <label for="etime">Report To</label>
                <flat-pickr v-model="etime" class="form-control" id="etime"
                            :config="{enableTime: true, dateFormat: 'Y-m-d H:i'}"></flat-pickr>
              </div>
              <div class="form-group mx-2">
                <label for="timezone">Timezone</label>
                <select v-model="timezone" class="form-control" id="timezone">
                  <option v-for="tz in timezones" :value="tz">{{tz}}</option>
                </select>
              </div>
            </div>
            <div class="d-flex">
              <div class="form-group">
                <label for="label">Report Label</label>
                <input type="text" id="label" v-model="label" class="form-control">
              </div>
            </div>
            <button type="submit" class="btn btn-primary" :disabled="!(stime && etime)">Make Report</button>
          </form>

          <div>
            <b-button class="my-2" variant="primary" @click="reload">
              Reload
            </b-button>
          </div>
        </div>

        <h3>Stats History</h3>
        <table class="table">
          <thead>
          <tr>
            <th>Report Term</th>
            <th>Label</th>
            <th>Status</th>
          </tr>
          </thead>
          <tbody>
          <tr v-for="stat in stats">
            <td>
              <router-link v-if="stat.status === 'COMPLETE'"
                :to="{name: 'Container-Stats-StatId', params: {org: $route.params.org, name: $route.params.name, statid: stat.timestamp}}">
                {{ getTerm(stat) || stat.timestamp }}
              </router-link>
              <span v-else>
                {{ getTerm(stat) || stat.timestamp }}
              </span>
            </td>
            <td>{{stat.label}}</td>
            <td>{{stat.status}}</td>
          </tr>
          </tbody>
        </table>
      </div>
      <div class="col-3" v-else>
        Loading..
      </div>
    </div>
  </div>
</template>

<script>
  import moment from 'moment-timezone'
  import flatPickr from 'vue-flatpickr-component'

  export default {
    components: {flatPickr},
    data () {
      return {
        name: null,
        stats: null,
        stime: null,
        etime: null,
        label: null,
        node: null,
        timezone: 'UTC',
        timezones: moment.tz.names(),
        thresholdCount: 1
      }
    },
    async created () {
      const name = this.$route.params.name
      this.name = name
      await this.reload()
    },
    methods: {
      async makeReport () {
        const toast = this.$toasted.show('Request stats..')
        const body = {}
        if (this.stime) {
          body.stime = parseInt(moment.tz(this.stime, this.timezone).format('x'))
        }
        if (this.etime) {
          body.etime = parseInt(moment.tz(this.etime, this.timezone).format('x'))
        }
        if (this.label) {
          body.label = this.label
        }

        await this.$Amplify.API.post('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.name}/stats`, {body})
        toast.goAway(0)
        this.$toasted.show('Requested!', {duration: 3000})
        this.label = null
        await this.reload()
      },
      getTerm (stat) {
        return `${moment(stat.stime).format('YYYY/MM/DD HH:mm:ss')} 〜 ${moment(stat.etime).format('YYYY/MM/DD HH:mm:ss')}`
      },
      async reload () {
        this.stats = null
        const stats = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.name}/stats`)
        this.stats = stats.items
      }
    }
  }
</script>
