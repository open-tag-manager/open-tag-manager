<template>
  <div>
    <router-view :key="$route.fullPath"></router-view>

    <b-modal id="setting-modal" title="Setting" @ok="saveSetting">
      <div class="form-group">
        <label for="swagger-doc">Swagger Doc (JSON)</label>
        <textarea id="swagger-doc" class="form-control" v-model="swaggerDoc" rows="10"></textarea>
      </div>
    </b-modal>

    <div class="container py-2">
      <div v-if="stats">
        <button type="button" class="btn btn-primary" v-b-modal.setting-modal>Setting</button>

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
              <input type="text" id="label" v-model="label" class="form-control" pattern="[a-zA-Z]+">
            </div>
          </div>
          <button type="submit" class="btn btn-primary" :disabled="!(stime && etime)">Make Report</button>
        </form>

        <div>
          <b-button class="my-2" variant="primary" @click="reload">
            Reload
          </b-button>
        </div>

        <ul>
          <li v-for="stat in stats"><router-link :to="{name: 'Container-Stat-Graph', params: {org: $route.params.org, name: $route.params.name, statid: stat.key}}">{{ stat.key }}</router-link></li>
        </ul>
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
        swaggerDoc: '',
        thresholdCount: 1
      }
    },
    computed: {
      svgHeight () {
        if (this.isExpanded) {
          return window.innerHeight - 60
        } else {
          return 400
        }
      }
    },
    async created () {
      const name = this.$route.params.name
      this.name = name
      await this.reload()
      await this.getSwaggerDoc()
    },
    methods: {
      async makeReport () {
        const toast = this.$toasted.show('Request stats..')
        const body = {}
        if (this.stime) {
          body.stime = moment.tz(this.stime, this.timezone).format('x')
        }
        if (this.etime) {
          body.etime = moment.tz(this.etime, this.timezone).format('x')
        }
        if (this.label) {
          body.label = this.label
        }

        await this.$Amplify.API.post('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.name}/stats`, {body})
        toast.goAway(0)
        this.$toasted.show('Requested!', {duration: 3000})
        this.label = null
      },
      async reload () {
        this.stats = null
        const stats = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.name}/stats`)
        this.stats = stats
      },
      async getSwaggerDoc () {
        const data = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.name}/swagger_doc`)
        this.swaggerDoc = JSON.stringify(data)
      },
      async saveSwaggerDoc () {
        await this.$Amplify.API.put('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.name}/swagger_doc`, {body: JSON.parse(this.swaggerDoc)})
      },
      async saveSetting () {
        await this.saveSwaggerDoc()
      }
    }
  }
</script>

<style>
  #graph .node rect, #graph .node ellipse {
    stroke: #333;
    fill: #fff;
    stroke-width: 1.5px;
  }

  #graph path {
    stroke: #333;
    fill: none;
    stroke-width: 1.5px;
  }

  #graph .arrowhead {
    stroke: #333;
    fill: #333;
    stroke-width: 1.5px;
  }

  #graph .clusters rect {
    fill: #fff;
    stroke: #333;
    stroke-width: 1.5px;
  }

  .graph-container {
    position: relative;
  }

  .graph-container .node-info {
    position: absolute;
    left: 0;
    bottom: 0;
    padding: 5px;
    background: #fff;
    max-width: 50vw;
    opacity: 0.8;
  }

  .graph-container .graph-operation {
    position: absolute;
    right: 0;
    bottom: 0;
    padding: 5px;
  }
</style>
