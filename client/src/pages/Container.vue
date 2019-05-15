<template>
  <div class="container-fluid" :key="$route.params.name">
    <div class="row">
      <div class="col-2 bg-light sidebar py-4">
        <b-form-select class="mb-4" v-model="currentContainer" @change="changeContainer">
          <option :value="container.name" v-for="container in $store.state.container.containers" :key="container.name">
            {{container.label}} ({{container.name}})
          </option>
        </b-form-select>

        <b-nav vertical>
          <b-nav-item :to="{name: 'Container-Stat', params: {org: $route.params.org, name: $route.params.name}}">
            Analytics
          </b-nav-item>
          <b-nav-item :to="{name: 'Container-Setting', params: {org: $route.params.org, name: $route.params.name}}">
            Setting
          </b-nav-item>
        </b-nav>
      </div>
      <div role="main" class="col-10 px-4">
        <router-view></router-view>
      </div>
    </div>
  </div>
</template>

<script>
  import _ from 'lodash'

  export default {
    async mounted () {
      await this.$store.dispatch('container/fetchContainers', {org: this.$route.params.org})
      const container = _.find(this.$store.state.container.containers, {name: this.$route.params.name})
      if (container) {
        this.$store.dispatch('container/setCurrentContainer', {container})
      }
    },
    computed: {
      currentContainer: {
        get () {
          const container = this.$store.state.container.container
          if (container) {
            return container.name
          }

          return null
        },
        set (val) {
          const container = _.find(this.$store.state.container.containers, {name: val})
          this.$store.dispatch('container/setCurrentContainer', {container})
        }
      }
    },
    methods: {
      changeContainer () {
        this.$router.push(`/orgs/${this.$route.params.org}/containers/${this.currentContainer}/stat`)
      }
    }
  }
</script>

<style scoped>
  .sidebar {
    position: sticky;
    z-index: 1000;
    top: 56px;
    height: calc(100vh - 56px);
    overflow: scroll;
  }

  .router-link-active {
    font-weight: bold;
  }
</style>
