<template>
  <div>
    Stat
    <nuxt-child></nuxt-child>
  </div>
</template>

<script>
import { Component, Vue } from 'vue-property-decorator'

@Component
export default class AnalyticsStat extends Vue {}
</script>
