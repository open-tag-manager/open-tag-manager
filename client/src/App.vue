<template>
  <div id="app">
    <header>
      <b-navbar toggleable="md" type="dark" fixed class="bg-dark">
        <router-link :to="{name: 'Top'}">
          <b-navbar-brand>Open Tag Manager</b-navbar-brand>
        </router-link>

        <b-navbar-nav class="ml-auto">
          <b-nav-item @click.prevent="logout" v-if="$store.getters['user/isAuthenticated']">Sign out</b-nav-item>
          <b-nav-item to="/login" v-else>Sign in</b-nav-item>
        </b-navbar-nav>
      </b-navbar>
    </header>
    <router-view/>
  </div>
</template>

<script>
  export default {
    name: 'App',
    methods: {
      logout () {
        this.$store.dispatch('user/logout')
        this.$router.push('/')
      }
    }
  }
</script>

<style>
</style>
