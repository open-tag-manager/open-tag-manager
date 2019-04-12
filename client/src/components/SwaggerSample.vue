<template>
  <div>
    <button class="btn btn-primary" @click="reset" v-if="!isSample">Reset</button>
    <button class="btn btn-primary" @click="showSample" v-if="!isSample">Swagger Sample</button>
    <button class="btn btn-primary" @click="isSample = false" v-if="isSample">Edit</button>
    <swagger-sample-children
      v-if="tree && tree.children.length > 0"
      :children="tree.children"
      @aggregate="aggregate" v-show="!isSample"
    ></swagger-sample-children>
    <div v-if="isSample">
      <textarea readonly :value="sampleJson" class="form-control" rows="15"></textarea>
    </div>
  </div>
</template>

<script>
  import {getPathSample} from '../lib/UrlTree'
  import SwaggerSampleChildren from './SwaggerSampleChildren'
  import _ from 'lodash'

  const findNode = function (children, id) {
    const n = _.find(children, {id})
    if (n) {
      return n
    }

    const f = children.map((c) => {
      if (c.children.length === 0) {
        return null
      }

      return findNode(c.children, id)
    })

    const r = _.reject(f, _.isEmpty)
    if (r.length > 0) {
      return r[0]
    }

    return null
  }

  export default {
    components: {SwaggerSampleChildren},
    data () {
      return {
        tree: null,
        isSample: false,
        sample: null
      }
    },
    props: {
      urlTree: {
        type: Object,
        required: true
      }
    },
    mounted () {
      this.reset()
    },
    computed: {
      sampleJson () {
        return JSON.stringify(this.sample, null, 2)
      }
    },
    methods: {
      reset () {
        this.tree = _.cloneDeep(this.urlTree)
      },
      aggregate (d) {
        const tree = _.cloneDeep(this.tree)
        console.log(d.node.id)
        const node = findNode(tree.children, d.node.id)
        console.log(node)
        if (!node) {
          return null
        }
        const newNode = {
          path: `{${d.name}}`,
          id: `${node.id}/${d.name}`,
          children: null,
          level: node.level + 1,
          exists: true
        }
        let newChildren = []
        node.children.forEach((c) => {
          c.children.forEach((gc) => {
            if (!_.find(newChildren, {path: gc.path})) {
              newChildren.push(gc)
            }
          })
        })
        newNode.children = newChildren
        node.children = [newNode]
        this.tree = tree
      },
      showSample () {
        this.sample = getPathSample(this.tree)
        console.log(this.sample)
        this.isSample = true
      }
    }
  }
</script>
