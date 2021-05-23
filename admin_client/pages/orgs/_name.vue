<template>
  <div>
    <nuxt-child />
  </div>
</template>

<script>
import { Component, Vue } from 'nuxt-property-decorator'

@Component({ middleware: 'authenticated' })
export default class OrgsName extends Vue {}
</script>
