<template>
  <ul>
    <li v-for="child in children" :key="child.path">
      <div class="mr-2">/{{child.path}}</div>

      <ul v-if="child.children.length > 0">
        <li>
          <form class="d-flex" @submit.prevent="aggregate(child, pathParamName[child.path])">
            <input type="text" class="form-control mr-2" placeholder="Aggregation path parameter name" required
                   v-model="pathParamName[child.path]">
            <button type="submit" class="btn btn-primary btn-sm" v-if="child.children.length > 0">A</button>
          </form>
        </li>
      </ul>

      <swagger-sample-children :children="child.children" @aggregate="childAggregate">
      </swagger-sample-children>
    </li>
  </ul>
</template>

<script>
  export default {
    name: 'SwaggerSampleChildren',
    data () {
      const pathParamName = {}
      this.children.forEach((c) => {
        pathParamName[c.path] = ''
      })

      return {pathParamName}
    },
    props: {
      children: {
        type: Array,
        required: true
      }
    },
    methods: {
      aggregate (child, name) {
        this.$emit('aggregate', {node: child, name})
      },
      childAggregate (d) {
        this.$emit('aggregate', d)
      }
    }
  }
</script>
