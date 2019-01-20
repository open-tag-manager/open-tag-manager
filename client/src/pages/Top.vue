<template>
  <div class="container py-2">
    <b-jumbotron header="Open Tag Manager">
      <router-link v-if="!$store.getters['user/isAuthenticated']" :to="{name: 'Auth'}">Sign in</router-link>
      <div v-if="$store.getters['user/isAuthenticated']" class="w-25 my-2">
        Select org:
        <b-form-select v-model="currentOrg">
          <option :value="org" v-for="org in $store.state.user.orgs" :key="org.org">{{org.org}}</option>
        </b-form-select>
      </div>
      <router-link v-if="$store.getters['user/isAuthenticated']" :to="{name: 'Containers', params: {org: currentOrg.org}}">Containers List
      </router-link>
    </b-jumbotron>
  </div>
</template>

<script>
  export default {
    computed: {
      currentOrg: {
        get () {
          return this.$store.state.user.currentOrg
        },
        set (org) {
          this.$store.dispatch('user/setCurrentOrg', org)
        }
      }
    }
  }
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
  h1, h2 {
    font-weight: normal;
  }

  ul {
    list-style-type: none;
    padding: 0;
  }

  li {
    display: inline-block;
    margin: 0 10px;
  }

  a {
    color: #42b983;
  }
</style>
