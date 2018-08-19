<template>
</template>

<script>
  export default {
    created () {
      if (this.$route.name === 'Container-Home') {
        this.$router.push({name: 'Container-Setting', params: {name: this.$route.params.name}})
      }
    }
  }
</script>
