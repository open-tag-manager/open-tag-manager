<template>
  <table class="table table-striped">
    <thead>
    <tr>
      <th scope="col">URL</th>
      <th scope="col">Count</th>
      <th scope="col">Session</th>
      <th scope="col">User</th>
      <th scope="col">Scroll(AVG)</th>
      <th scope="col">Scroll(MAX)</th>
    </tr>
    </thead>
    <tbody>
    <tr v-for="col in data">
      <td><a @click.prevent="clickUrl(col.url)" href="#">{{col.url}}</a></td>
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
        this.$emit('clickUrl', url)
      }
    }
  }
</script>
