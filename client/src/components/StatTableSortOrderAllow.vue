<template>
  <span v-if="isAsc">↓</span>
  <span v-else="isDesc">↑</span>
</template>

<script>
  export default {
    props: {
      order: {
        type: String,
        required: true
      }
    },
    computed: {
      isAsc() {
        return this.order === 'asc'
      },
      isDesc() {
        return this.order === 'desc'
      }
    }
  }
</script>
