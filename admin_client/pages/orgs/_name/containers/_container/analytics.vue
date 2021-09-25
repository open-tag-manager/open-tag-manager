<template>
  <div class="stat-navigation">
    <nav>
      <ul class="pa-2">
        <li>
          <nuxt-link
            :to="{
              name: 'orgs-name-containers-container-analytics-url_table',
              params: routePrams,
              query: $route.query,
            }"
          >
            URL Table
          </nuxt-link>
        </li>
        <li>
          <nuxt-link
            :to="{
              name: 'orgs-name-containers-container-analytics-event_table',
              params: routePrams,
              query: $route.query,
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

<script>
import { Component } from 'vue-property-decorator'
import OrgContainer from '~/components/OrgContainer'

@Component
export default class StatMenu extends OrgContainer {
  get routePrams() {
    return {
      name: this.$route.params.name,
      container: this.$route.params.container,
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
