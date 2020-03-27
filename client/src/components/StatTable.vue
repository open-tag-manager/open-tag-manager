<template>
  <table class="table table-striped">
    <thead>
    <tr>
      <th scope="col" @click="sort('url')">URL
        <stat-table-sort-order-allow v-if="sortBy === 'url'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col"></th>
      <th scope="col"></th>
      <th scope="col"></th>
      <th scope="col" @click="sort('count')">PV
        <stat-table-sort-order-allow v-if="sortBy === 'count'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('session_count')">Session
        <stat-table-sort-order-allow v-if="sortBy === 'session_count'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('user_count')">User
        <stat-table-sort-order-allow v-if="sortBy === 'user_count'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('event_count')">Event
        <stat-table-sort-order-allow v-if="sortBy === 'event_count'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('w_click_count')">Widget Click
        <stat-table-sort-order-allow v-if="sortBy === 'w_click_count'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('t_click_count')">Trivial Click
        <stat-table-sort-order-allow v-if="sortBy === 't_click_count'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('avg_scroll_y')">Scroll(AVG)
        <stat-table-sort-order-allow v-if="sortBy === 'avg_scroll_y'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('max_scroll_y')">Scroll(MAX)
        <stat-table-sort-order-allow v-if="sortBy === 'max_scroll_y'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('avg_plt')">FP (AVG)
        <stat-table-sort-order-allow v-if="sortBy === 'avg_plt'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('max_plt')">FP (MAX)
        <stat-table-sort-order-allow v-if="sortBy === 'max_plt'" :order="order"></stat-table-sort-order-allow>
      </th>
    </tr>
    </thead>
    <tbody>
    <tr v-for="col in sortedData">
      <td class="url">{{col.url}}</td>
      <td><a @click.prevent="clickUrl(col.url)" href="#">Show Graph</a></td>
      <td><a @click.prevent="filterUrl(col.url)" href="#">Filter in Line Chart</a></td>
      <td><a @click.prevent="showEvent(col.url)" href="#">Show Event Table</a></td>
      <td>{{col.count}}</td>
      <td>{{col.session_count}}</td>
      <td>{{col.user_count}}</td>
      <td>{{col.event_count}}</td>
      <td>{{col.w_click_count}}</td>
      <td>{{col.t_click_count}}</td>
      <td>{{col.avg_scroll_y}}</td>
      <td>{{col.max_scroll_y}}</td>
      <td>{{col.avg_plt}}</td>
      <td>{{col.max_plt}}</td>
    </tr>
    </tbody>
  </table>
</template>

<script>
  import _ from 'lodash'
  import StatTableSortOrderAllow from './StatTableSortOrderAllow'

  export default {
    components: {StatTableSortOrderAllow},
    data () {
      return {
        sortBy: null,
        order: 'asc'
      }
    },
    props: {
      data: {
        type: Array,
        required: true
      }
    },
    computed: {
      sortedData () {
        if (!this.sortBy) {
          return this.data
        }

        return _.clone(this.data).sort((a, b) => {
          const bi = this.order === 'asc' ? 1 : -1

          if (a[this.sortBy] === null) {
            return 1
          }
          if (b[this.sortBy] === null) {
            return -1
          }

          if (a[this.sortBy] > b[this.sortBy]) {
            return 1 * bi
          }

          if (a[this.sortBy] < b[this.sortBy]) {
            return -1 * bi
          }

          return 0
        })
      }
    },
    methods: {
      clickUrl (url) {
        this.$emit('clickGraphUrl', url)
      },
      filterUrl (url) {
        this.$emit('clickFilterUrl', url)
      },
      showEvent (url) {
        this.$emit('clickShowEvent', url)
      },
      sort (field) {
        if (this.sortBy === field) {
          this.order = this.order === 'asc' ? 'desc' : 'asc'
        } else {
          this.order = 'desc'
          this.sortBy = field
        }
      }
    }
  }
</script>

<style scoped>
  .url {
    font-size: 0.8em;
    word-break: break-all;
  }
</style>
