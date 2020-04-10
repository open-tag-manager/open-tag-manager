<template>
  <div>
    <div class="py-2">
      <ol class="breadcrumb align-items-center">
        <li class="breadcrumb-item"><b-link :to="{name: 'Container-Stats', params: {org: $route.params.org, name: $route.params.name}}">Analytics</b-link></li>
        <li class="breadcrumb-item">{{statTerm}}<span v-if="statLabel">({{statLabel}})</span></li>
        <li class="breadcrumb-item">
          <b-form-select class="menu-select" :value="currentPage" @change="changePage">
            <option value="Container-Stats-StatId-Pages">Pages Table</option>
            <option value="Container-Stats-StatId-Events">Events Table</option>
            <option value="Container-Stats-StatId-URLGraph">URL Graph</option>
            <option value="Container-Stats-StatId-URLTree">URL Tree</option>
          </b-form-select>
        </li>
        <li class="breadcrumb-item" v-if="$route.name === 'Container-Stats-StatId-URLGraph-URL'">
          Event Graph
        </li>
      </ol>

      <div>
        <router-view></router-view>
      </div>
    </div>
  </div>
</template>

<script>
  import {statIdToInfo} from '../lib/StatId'

  export default {
    async mounted () {
      if (this.$route.name === 'Container-Stats-StatId') {
        this.$router.push({name: 'Container-Stats-StatId-Pages', params: this.$route.params})
      }
    },
    computed: {
      statinfo () {
        return statIdToInfo(this.$route.params.statid)
      },
      statTerm () {
        return this.statinfo.term
      },
      statLabel () {
        return this.statinfo.label
      },
      currentPage () {
        if (this.$route.name === 'Container-Stats-StatId-URLGraph-URL') {
          return 'Container-Stats-StatId-URLGraph'
        }

        return this.$route.name
      }
    },
    methods: {
      changePage (i) {
        this.$router.push({name: i, params: this.$route.params})
      }
    }
  }
</script>

<style scoped>
  .menu-select {
    width: 150px;
  }
</style>
