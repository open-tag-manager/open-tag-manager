<template>
  <div>
    <div class="alert alert-warning" v-if="$store.state.user.currentOrg.freezed">
      <fa-icon icon="exclamation-triangle"/> This org is freezed
    </div>

    <div class="container p-2 text-center" v-if="noPermission">
      <div class="alert alert-warning">
        <fa-icon icon="exclamation-triangle"/> Permission error
      </div>
    </div>
    <router-view v-else></router-view>
  </div>
</template>

<script>
  import _ from 'lodash'

  export default {
    data () {
      return {
        noPermission: false
      }
    },
    async beforeRouteUpdate (to, from, next) {
      await this.setCurrentOrg()
      next()
    },
    async mounted () {
      await this.setCurrentOrg()
    },
    methods: {
      async setCurrentOrg () {
        const orgName = this.$route.params.org
        const orgs = this.$store.state.user.orgs
        let org = _.find(orgs, {org: orgName})
        if (org) {
          if (!this.$store.getters['user/hasRootRole'] && !_.find(org.roles, 'read')) {
            this.noPermission = true
            return
          }
        } else {
          if (this.$store.getters['user/hasRootRole']) {
            org = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}`)
            org.roles = ['read', 'write', 'admin']
          } else {
            this.noPermission = true
            return
          }
        }
        const o = _.cloneDeep(org)
        this.$store.dispatch('user/setCurrentOrg', o)
      }
    }
  }
</script>
