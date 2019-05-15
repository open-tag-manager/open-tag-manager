<template>
  <div :key="$route.params.org">
    <div class="container p-2 text-center" v-if="noPermission">
      <fa-icon icon="exclamation-triangle"/> Permission error
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
    created () {
      const orgName = this.$route.params.org
      const orgs = this.$store.state.user.orgs
      const org = _.find(orgs, {org: 'root'}) || _.find(orgs, {org: orgName})
      if (!org) {
        this.noPermission = true
        return
      }
      if (_.find(org.roles, 'read')) {
        this.noPermission = true
        return
      }
      const o = _.cloneDeep(org)
      o.org = orgName
      this.$store.dispatch('user/setCurrentOrg', o)
    }
  }
</script>
