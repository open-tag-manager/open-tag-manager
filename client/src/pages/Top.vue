<template>
  <div class="container py-2">
    <b-jumbotron>
      <h1 class="text-center display-4 mb-4">Open Tag Manager</h1>
      <div class="text-center">
        <router-link class="btn btn-primary btn-lg" :to="{name: 'Auth'}">
          Sign in
        </router-link>
      </div>
    </b-jumbotron>
  </div>
</template>

<script>
  export default {}
</script>
