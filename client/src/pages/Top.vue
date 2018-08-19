<template>
  <div class="container py-2">
    <b-jumbotron header="Open Tag Manager">
      <router-link v-if="!$store.getters['user/isAuthenticated']" :to="{name: 'Login'}">Sign in</router-link>
      <router-link v-if="$store.getters['user/isAuthenticated']" :to="{name: 'Containers'}">Containers List</router-link>
    </b-jumbotron>
  </div>
</template>

<script>
  export default {
    name: 'top'
  }
</script>
