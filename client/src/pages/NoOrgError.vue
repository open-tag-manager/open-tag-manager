<template>
  <div class="container p-2 text-center">
    <fa-icon icon="exclamation-triangle" /> Organization is not set
  </div>
</template>

<script>
  export default {
    mounted () {
      if (this.$store.state.user.orgs.length > 0) {
        this.$router.push('/')
      }
    }
  }
</script>
