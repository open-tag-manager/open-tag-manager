<template>
  <div class="stat-navigation">
    <nav>
      <ul class="pa-2">
        <li>
          <nuxt-link
            :to="{
              name: 'orgs-name-containers-container-analytics-stat-url_table',
              params: routePrams,
            }"
          >
            URL Table
          </nuxt-link>
        </li>
        <li>
          <nuxt-link
            :to="{
              name: 'orgs-name-containers-container-analytics-stat-event_table',
              params: routePrams,
            }"
          >
            Event Table
          </nuxt-link>
        </li>
      </ul>
    </nav>
    <nuxt-child></nuxt-child>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator'

@Component
export default class AnalyticsStat extends Vue {
  get routePrams() {
    return {
      name: this.$route.params.name,
      container: this.$route.params.container,
      stat: this.$route.params.stat,
    }
  }
}
</script>

<style lang="scss" scoped>
.stat-navigation {
  nav {
    ul {
      li {
        list-style-type: none;
        display: inline-block;
        padding: 8px;

        .nuxt-link-active {
          font-weight: bold;
        }
      }
    }
  }
}
</style>
