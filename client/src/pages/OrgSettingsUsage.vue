<template>
  <div class="container py-2">
    <h2>Usage report</h2>

    <table class="table">
      <thead>
      <tr>
        <th>
          Month
        </th>
        <th>
          Athena Scan (bytes)
        </th>
        <th>
          Collect (numbers)
        </th>
        <th>
          Details
        </th>
      </tr>
      </thead>

      <tbody>
      <tr v-for="usage in usages" :key="usage.month">
        <td>
          {{ usage.month }}
        </td>
        <td>
          {{ usage.athena_scan_size }}
        </td>
        <td>
          {{ usage.collect_size }}
        </td>
        <td>
          <ul>
            <li v-for="detail in usage.details" :key="detail.type + detail.tid">{{detail.type}}({{detail.tid}}): {{detail.size}}</li>
          </ul>
        </td>
      </tr>
      </tbody>
    </table>

  </div>
</template>

<script>
  export default {
    data () {
      return {
        usages: []
      }
    },
    async created () {
      await this.load()
    },
    methods: {
      async load () {
        const data = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/usages`)
        this.usages = data.items
      }
    }
  }
</script>
