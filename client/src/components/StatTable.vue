<template>
  <table class="table table-striped">
    <thead>
    <tr>
      <th scope="col">URL</th>
      <th scope="col"></th>
      <th scope="col"></th>
      <th scope="col">Count</th>
      <th scope="col">Session</th>
      <th scope="col">User</th>
      <th scope="col">Scroll(AVG)</th>
      <th scope="col">Scroll(MAX)</th>
    </tr>
    </thead>
    <tbody>
    <tr v-for="col in data">
      <td>{{col.url}}</td>
      <td><a @click.prevent="clickUrl(col.url)" href="#">Show Graph</a></td>
      <td><a @click.prevent="filterUrl(col.url)" href="#">Filter in Line Chart</a></td>
      <td>{{col.count}}</td>
      <td>{{col.session_count}}</td>
      <td>{{col.user_count}}</td>
      <td>{{col.avg_scroll_y}}</td>
      <td>{{col.max_scroll_y}}</td>
    </tr>
    </tbody>
  </table>
</template>

<script>
  export default {
    props: {
      data: {
        type: Array,
        required: true
      }
    },
    methods: {
      clickUrl (url) {
        this.$emit('clickGraphUrl', url)
      },
      filterUrl (url) {
        this.$emit('clickFilterUrl', url)
      }
    }
  }
</script>
