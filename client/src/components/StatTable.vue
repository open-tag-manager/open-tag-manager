<template>
  <table class="table table-striped">
    <thead>
    <tr>
      <th scope="col">URL</th>
      <th scope="col"></th>
      <th scope="col"></th>
      <th scope="col">PV</th>
      <th scope="col">Session</th>
      <th scope="col">User</th>
      <th scope="col">Event</th>
      <th scope="col">Widget Click</th>
      <th scope="col">Trivial Click</th>
      <th scope="col">Scroll(AVG)</th>
      <th scope="col">Scroll(MAX)</th>
    </tr>
    </thead>
    <tbody>
    <tr v-for="col in data">
      <td class="url">{{col.url}}</td>
      <td><a @click.prevent="clickUrl(col.url)" href="#">Show Graph</a></td>
      <td><a @click.prevent="filterUrl(col.url)" href="#">Filter in Line Chart</a></td>
      <td>{{col.count}}</td>
      <td>{{col.session_count}}</td>
      <td>{{col.user_count}}</td>
      <td>{{col.event_count}}</td>
      <td>{{col.w_click_count}}</td>
      <td>{{col.t_click_count}}</td>
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

<style scoped>
  .url {
    font-size: 0.8em;
    word-break: break-all;
  }
</style>
