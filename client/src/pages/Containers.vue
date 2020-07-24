<template>
</template>

<script>
  export default {
    async created () {
      await this.$store.dispatch('container/fetchContainers', {org: this.$route.params.org})
      if (this.$store.state.container.containers.length > 0) {
        this.$router.push(`/orgs/${this.$route.params.org}/containers/${this.$store.state.container.containers[0].tid}/stats`)
        return
      }

      this.$router.push(`/orgs/${this.$route.params.org}/settings/containers`)
    }
  }
</script>
