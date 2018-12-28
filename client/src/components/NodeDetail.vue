<template>
  <div class="node-detail">
    <div><span class="label">Event:</span> {{node.name}}</div>
    <div><span class="label">URL:</span> <a :href="nodeUrl" target="_blank">{{ node.url }}</a></div>
    <div><span class="label">Label:</span> {{ node.label }}</div>
    <div><span class="label">XPath:</span> {{node.xpath}}</div>
    <div><span class="label">ID:</span> {{node.a_id}}</div>
    <div><span class="label">Class:</span> {{node.class}}</div>
  </div>
</template>

<script>
  import url from 'url'

  export default {
    props: {
      node: {
        type: Object,
        required: true
      }
    },
    computed: {
      nodeUrl () {
        if (this.node && this.node.url) {
          const parsedUrl = url.parse(this.node.url, true)
          parsedUrl.query._op = '1'
          parsedUrl.query._op_id = this.node.a_id
          parsedUrl.query._op_xpath = this.node.xpath
          return url.format(parsedUrl)
        }

        return ''
      }
    }
  }
</script>

<style scoped>
  .node-detail {
    max-height: 200px;
    overflow: auto;
  }

  .node-detail .label {
    font-weight: bold;
  }
</style>
