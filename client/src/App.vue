<template>
  <div id="app">
    <b-navbar toggleable="md" type="dark" sticky class="bg-dark">
      <router-link :to="{name: 'Top'}">
        <b-navbar-brand>Open Tag Manager</b-navbar-brand>
      </router-link>

      <b-navbar-nav class="ml-auto" v-if="$store.state.user.user">
        <b-nav-text class="mr-2">
          <fa-icon icon="user"></fa-icon>
          {{$store.state.user.user.username}}
        </b-nav-text>
        <b-nav-text class="mr-1">
          <fa-icon icon="building"></fa-icon>
        </b-nav-text>
        <b-nav-form class="mr-2">
          <b-form-select v-model="currentOrg" @change="changeOrg">
            <option :value="org" v-for="org in $store.state.user.orgs" :key="org.org">{{org.org}}</option>
          </b-form-select>
        </b-nav-form>
        <b-nav-item :to="'/orgs/' + currentOrg.org + '/settings/containers'" v-if="currentOrg">
          <fa-icon icon="cog"></fa-icon>
          Setting
        </b-nav-item>
        <b-nav-item href="#" @click.prevent="signOut">Sign out
        </b-nav-item>
      </b-navbar-nav>
      <b-navbar-nav class="ml-auto" v-else>
        <b-nav-item to="/login">Sign in</b-nav-item>
      </b-navbar-nav>
    </b-navbar>
    <router-view/>
  </div>
</template>

<script>
  export default {
    data () {
      return {
        selected: null
      }
    },
    computed: {
      currentOrg: {
        get () {
          return this.$store.state.user.currentOrg
        },
        set (org) {
          this.$store.dispatch('user/setCurrentOrg', org)
        }
      }
    },
    methods: {
      async signOut () {
        await this.$store.dispatch('user/signOut')
        this.$router.push('/')
      },
      changeOrg () {
        this.$router.push(`/orgs/${this.currentOrg.org}/containers`)
      }
    }
  }
</script>
