<template>
  <table class="table table-striped">
    <thead>
    <tr>
      <th scope="col" @click="sort('url')">URL
        <stat-table-sort-order-allow v-if="sortBy === 'url'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('title')">Title
        <stat-table-sort-order-allow v-if="sortBy === 'title'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('state')">Event
        <stat-table-sort-order-allow v-if="sortBy === 'state'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('label')">Label
        <stat-table-sort-order-allow v-if="sortBy === 'label'" :order="order"></stat-table-sort-order-allow>
      </th>
      <th scope="col" @click="sort('count')">Count
        <stat-table-sort-order-allow v-if="sortBy === 'count'" :order="order"></stat-table-sort-order-allow>
      </th>
    </tr>
    </thead>
    <tbody>
    <tr v-for="r in sortedData" :key="r.url + ' ' + r.state">
      <td class="url">{{r.url}}</td>
      <td class="title">{{r.title}}</td>
      <td class="state">{{r.state}}</td>
      <td class="label">{{r.label}}</td>
      <td>{{r.count}}</td>
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
      },
      filterState: {
        type: String
      },
      filterStates: {
        type: Array
      },
      filterUrl: {
        type: String
      }
    },
    computed: {
      sortedData () {
        let data = this.data
        if (this.filterState) {
          data = _.filter(data, {state: this.filterState})
        } else {
          data = _.filter(data, (d) => {
            if (d.state) {
              for (let pattern of this.filterStates) {
                if (d.state.match(pattern)) {
                  return true
                }
              }
            }

            return false
          })
        }

        if (this.filterUrl) {
          data = _.filter(data, {url: this.filterUrl})
        }

        if (!this.sortBy) {
          return data
        }

        return _.clone(data).sort((a, b) => {
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
  .url, .title, .state, .label {
    font-size: 0.8em;
    word-break: break-all;
  }
</style>
