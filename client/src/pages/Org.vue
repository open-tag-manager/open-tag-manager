<template>
  <div>
    <router-view></router-view>
  </div>
</template>

<script>
  import _ from 'lodash'

  export default {
    created () {
      const orgName = this.$route.params.org
      const orgs = this.$store.state.user.orgs
      const org = _.find(orgs, {org: 'root'}) || _.find(orgs, {org: orgName})
      if (!org) {
        this.$router.push('/')
        return
      }
      if (_.find(org.roles, 'read')) {
        this.$router.push('/')
        return
      }
      const o = _.cloneDeep(org)
      o.org = orgName
      this.$store.dispatch('user/setCurrentOrg', o)
    }
  }
</script>
