<template>
  <div id="app">
    <header>
      <b-navbar toggleable="md" type="dark" fixed class="bg-dark">
        <router-link :to="{name: 'Top'}">
          <b-navbar-brand>Open Tag Manager</b-navbar-brand>
        </router-link>

        <b-navbar-nav class="ml-auto">
          <b-nav-item href="#" @click.prevent="signOut" v-if="$store.getters['user/isAuthenticated']">Sign out</b-nav-item>
          <b-nav-item to="/login" v-else>Sign in</b-nav-item>
        </b-navbar-nav>
      </b-navbar>
    </header>
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
    methods: {
      async signOut () {
        await this.$store.dispatch('user/signOut')
        this.$router.push('/')
      }
    }
  }
</script>

<style>
</style>
