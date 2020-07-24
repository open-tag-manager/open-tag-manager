<template>
  <div>
    <h2 class="mb-2">URL Tree</h2>

    <swagger-sample :url-tree="urlTree" :original-url-tree="originalUrlTree" v-if="urlTree"
                    @save="saveSwaggerSample"/>
  </div>
</template>

<script>
  import {getTree} from '../lib/UrlTree'
  import axios from 'axios'
  import SwaggerSample from '../components/SwaggerSample'

  export default {
    components: {SwaggerSample},
    data () {
      return {
        urls: null,
        urlTree: null,
        originalUrlTree: null
      }
    },
    async mounted () {
      const stat = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.$route.params.name}/stats/${this.$route.params.statid}`)
      if (!stat) {
        return
      }
      const data = await axios.get(stat.file_url)
      this.urls = data.data.urls
      this.urlTree = getTree(this.urls, this.$store.getters['container/getSwaggetDocPaths'])
      this.originalUrlTree = getTree(this.urls)
    },
    methods: {
      async saveSwaggerSample ({sample}) {
        this.$store.dispatch('container/editSwaggerDoc', {swaggerDoc: JSON.stringify(sample)})
        await this.$store.dispatch('container/saveSwaggerDoc', {
          org: this.$route.params.org,
          container: this.$route.params.name
        })
      }
    }
  }
</script>
