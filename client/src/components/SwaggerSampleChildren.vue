<template>
  <ul>
    <li v-for="child in children" :key="child.path">
      <div class="mr-2" v-if="child.level === 1">/{{child.path}}</div>
      <b-checkbox v-if="child.level > 1" :checked="!check[child.path]" @input="changeCheck(child)">/{{child.path}}</b-checkbox>

      <ul v-if="child.children.length > 0">
        <li>
          <form class="d-flex" @submit.prevent="aggregate(child, pathParamName[child.path])">
            <input type="text" class="form-control mr-2" placeholder="Aggregation path parameter name" required
                   v-model="pathParamName[child.path]">
            <button type="submit" class="btn btn-primary btn-sm" v-if="child.children.length > 0">A</button>
          </form>
        </li>
      </ul>

      <swagger-sample-children :children="child.children" @aggregate="childAggregate" @changeCheck="childChangeCheck">
      </swagger-sample-children>
    </li>
  </ul>
</template>

<script>
  export default {
    name: 'SwaggerSampleChildren',
    data () {
      const pathParamName = {}
      const check = {}
      this.children.forEach((c) => {
        pathParamName[c.path] = ''
      })

      return {pathParamName, check}
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
      },
      changeCheck (child) {
        let check = !this.check[child.path]
        this.check[child.path] = check
        this.$emit('changeCheck', {node: child, check: !check})
      },
      childChangeCheck (d) {
        this.$emit('changeCheck', d)
      }
    }
  }
</script>
