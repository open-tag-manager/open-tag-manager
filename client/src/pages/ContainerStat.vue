<template>
  <div>
    <div class="container-fluid graph-container">
      <div id="graph">
        <div>
          Select report
        </div>
      </div>
      <div class="node-info" v-if="graphData">
        <div v-if="node" class="detail">
          <h3>Node Info</h3>
          <div><span class="label">Event:</span> {{node.name}}</div>
          <div><span class="label">URL:</span> {{ node.url }}</div>
          <div><span class="label">Label:</span> {{ node.label }}</div>
          <div><span class="label">XPath:</span> {{node.xpath}}</div>
        </div>

        <b-form-group label="Enabled Statuses" class="status-filter">
          <b-form-checkbox-group id="enabled-statuses" v-model="enabledStatues"
                                 :options="statuses" @input="r"></b-form-checkbox-group>
        </b-form-group>
      </div>

      <div v-if="graphData" class="graph-operation">
        <button class="wide-button btn btn-primary" @click="expand">
          <fa-icon icon="expand"></fa-icon>
        </button>
      </div>
    </div>
    <div class="container py-2">
      <div v-if="stats">
        <div>
          <div class="form-group">
            <label for="swagger-doc">Swagger Doc (JSON)</label>
            <textarea id="swagger-doc" class="form-control" v-model="swaggerDoc" rows="10"></textarea>
          </div>
        </div>

        <form @submit="makeReport" ref="form">
          <div class="d-flex align-items-center">
            <div class="form-group">
              <label for="stime">Report From</label>
              <flat-pickr v-model="stime" class="form-control" id="stime"
                          :config="{enableTime: true, dateFormat: 'Y-m-d H:i'}"></flat-pickr>
            </div>
            <div class="mx-2">〜</div>
            <div class="form-group">
              <label for="etime">Report To</label>
              <flat-pickr v-model="etime" class="form-control" id="etime"
                          :config="{enableTime: true, dateFormat: 'Y-m-d H:i'}"></flat-pickr>
            </div>
            <div class="form-group mx-2">
              <label for="timezone">Timezone</label>
              <select v-model="timezone" class="form-control" id="timezone">
                <option v-for="tz in timezones" :value="tz">{{tz}}</option>
              </select>
            </div>
          </div>
          <div class="d-flex">
            <div class="form-group">
              <label for="label">Report Label</label>
              <input type="text" id="label" v-model="label" class="form-control" pattern="[a-zA-Z]+">
            </div>
          </div>

          <b-button type="submit" class="my-2" variant="primary">
            Make Report
          </b-button>
        </form>

        <div>
          <b-button class="my-2" variant="primary" @click="reload">
            Reload
          </b-button>
        </div>

        <ul>
          <li v-for="stat in stats"><a href="#" @click.prevent="renderGraph(stat)">{{ stat.key }}</a></li>
        </ul>
      </div>
      <div class="col-3" v-else>
        Loading..
      </div>
    </div>
  </div>
</template>

<script>
  import api from '../api'
  import axios from 'axios'
  import * as d3 from 'd3'
  import * as DagreD3 from 'dagre-d3'
  import _ from 'lodash'
  import url from 'url'
  import moment from 'moment-timezone'
  import flatPickr from 'vue-flatpickr-component'
  import swaggerPaths from 'swagger-paths'

  const sourceFieldName = 'p_state'
  const targetFieldName = 'state'
  const countFieldName = 'count'

  const statusPatterns = {
    pageview: /^pageview$/,
    click_widget: /^click_widget.+/,
    click_trivial: /^click_trivial.+/,
    touchstart: /^touchstart_.+/,
    'change-url': /^change-url.+/,
    timer: /^timer_.+/,
    scroll: /^scroll_.+/
  }

  const findRelatedEdge = (data, edges, skipStatePatterns, results = [], path = []) => {
    for (let e of edges) {
      if (e[sourceFieldName] === e[targetFieldName]) {
        continue
      }
      let idx = _.findIndex(skipStatePatterns, (p) => {
        return e[sourceFieldName] && e[sourceFieldName].match(p)
      })
      if (idx === -1) {
        results.push(e)
      } else {
        // prevent circular reference
        let si = _.findIndex(path, (pe) => {
          return pe[sourceFieldName] && pe[sourceFieldName] === e[sourceFieldName]
        })
        if (si !== -1) {
          continue
        }

        let searchCondition = {}
        searchCondition[targetFieldName] = e[sourceFieldName]
        let deepEdges = _.filter(data, searchCondition)
        path.push(e)
        findRelatedEdge(data, deepEdges, skipStatePatterns, results, path)
      }
    }

    return results
  }

  const skipData = (data, skipStatePatterns = []) => {
    const cData = _.cloneDeep(data)
    // Mark as skip
    for (let d of cData) {
      let sourceMatched = false
      let targetMatched = false
      for (let pattern of skipStatePatterns) {
        if (d[sourceFieldName] && d[sourceFieldName].match(pattern)) sourceMatched = true
        if (d[targetFieldName] && d[targetFieldName].match(pattern)) targetMatched = true
      }
      d.sourceSkip = sourceMatched
      d.targetSkip = targetMatched
    }

    // Modify edge
    for (let d of cData) {
      if (d.targetSkip) {
        continue
      }
      if (d.sourceSkip) {
        let searchCondition = {}
        searchCondition[targetFieldName] = d[sourceFieldName]
        let edges = _.filter(data, searchCondition)
        edges = findRelatedEdge(data, edges, skipStatePatterns)
        for (let e of edges) {
          let searchCondition2 = {}
          searchCondition2[sourceFieldName] = e[sourceFieldName]
          searchCondition2[targetFieldName] = d[targetFieldName]
          let existsEdge = _.find(cData, searchCondition2)
          let count = e[countFieldName] > d[countFieldName] ? d[countFieldName] : e[countFieldName]
          if (existsEdge) {
            existsEdge[countFieldName] += count
          } else {
            let newEdge = {}
            newEdge[sourceFieldName] = e[sourceFieldName]
            newEdge[targetFieldName] = d[targetFieldName]
            newEdge.url = d.url
            newEdge.title = d.title
            newEdge.label = d.label
            newEdge.xpath = d.xpath
            newEdge[countFieldName] = count
            cData.push(newEdge)
          }
        }
      }
    }

    // Delete skipped edge
    return _.reject(_.reject(cData, 'sourceSkip'), 'targetSkip')
  }

  const convertUrl = (data, swaggerDoc) => {
    if (!swaggerDoc) {
      return data
    }
    const paths = new swaggerPaths(JSON.parse(swaggerDoc).paths)
    for (let d of data) {
      const parsedUrl = url.parse(d.url)
      if (!parsedUrl.path) {
        continue
      }

      let path = parsedUrl.path
      if (parsedUrl.hash) {
        const match = parsedUrl.hash.match(/^#!(\/.*)/)
        if (match) {
          const hashUrl = url.parse(match[1])
          path = hashUrl.path
        }
      }

      const matched = paths.match(path)
      if (matched) {
        d.url = matched.path.path
      }
    }

    return data
  }

  export default {
    components: {flatPickr},
    data () {
      return {
        name: null,
        stats: null,
        graphData: null,
        rawGraphData: null,
        stime: null,
        etime: null,
        label: null,
        node: null,
        timezone: 'UTC',
        timezones: moment.tz.names(),
        statuses: _.keys(statusPatterns),
        enabledStatues: _.difference(_.keys(statusPatterns), ['timer', 'scroll']),
        isExpanded: false,
        swaggerDoc: ''
      }
    },
    computed: {
      svgHeight () {
        if (this.isExpanded) {
          return window.innerHeight - 60
        } else {
          return 400
        }
      }
    },
    async created () {
      const name = this.$route.params.name
      this.name = name
      await this.reload()
    },
    methods: {
      async makeReport () {
        const toast = this.$toasted.show('Request stats..')
        const body = {}
        if (this.stime) {
          body.stime = moment.tz(this.stime, this.timezone).format('x')
        }
        if (this.etime) {
          body.etime = moment.tz(this.etime, this.timezone).format('x')
        }
        if (this.label) {
          body.label = this.label
        }

        await api(this.$store).post(`containers/${this.name}/stats`, body)
        toast.goAway(0)
        this.$toasted.show('Requested!', {duration: 3000})
        this.label = null
      },
      async reload () {
        this.stats = null
        const data = await api(this.$store).get(`containers/${this.name}/stats`)
        const stats = data.data
        this.stats = stats
      },
      async renderGraph (stat) {
        const data = await axios.get(stat.url)
        this.rawGraphData = data.data.result
        this.node = null
        this.render()
      },
      expand () {
        const cl = d3.select('#graph')
        const svg = cl.select('#graph svg')
        this.isExpanded = !this.isExpanded
        svg.attr('height', this.svgHeight)
      },
      render () {
        console.log('render')
        const self = this

        this.graphData = _.cloneDeep(this.rawGraphData)
        this.graphData = skipData(this.graphData, _.values(_.pick(statusPatterns, _.difference(this.statuses, this.enabledStatues))))
        this.graphData = convertUrl(this.graphData, this.swaggerDoc)

        const cl = d3.select('#graph')
        const width = cl.node().clientWidth
        const height = this.svgHeight
        cl.selectAll('*').remove()
        const svg = cl.append('svg').attr('width', width).attr('height', height)
        const inner = svg.append('g')
        const g = new DagreD3.graphlib.Graph({compound: true}).setGraph({}).setDefaultEdgeLabel(function () {
          return {}
        })

        const nodesData = []
        const linksData = []
        const urls = []

        const color = d3.scaleOrdinal(d3.schemeCategory20)

        const strimwidth = function (text, size) {
          if (!text) {
            return ''
          }
          if (text.length < size) {
            return text
          }
          return text.replace(/[\n\r]/g, '').substr(0, size) + '...'
        }

        const minmax = d3.extent(this.graphData, function (o) {
          return parseInt(o[countFieldName])
        })

        this.graphData.forEach(function (o) {
          if (!o.label) {
            o.label = ''
          }
          let sourceIdx = _.findIndex(nodesData, {name: o[sourceFieldName]})
          if (sourceIdx === -1) {
            nodesData.push({name: o[sourceFieldName]})
          }
          let targetIdx = _.findIndex(nodesData, {name: o[targetFieldName]})
          if (targetIdx === -1) {
            nodesData.push({name: o[targetFieldName]})
          }
          targetIdx = _.findIndex(nodesData, {name: o[targetFieldName]})

          if (o.url) {
            if (_.indexOf(urls, o.url) === -1) {
              urls.push(o.url)
            }
          }
          nodesData[targetIdx].url = o.url
          nodesData[targetIdx].title = o.title
          nodesData[targetIdx].label = o.label
          nodesData[targetIdx].xpath = o.xpath
        })

        urls.forEach(function (url, idx) {
          g.setNode(`url-${idx}`, {label: url, clusterLabelPos: 'top', style: 'fill: ' + color(url)})
        })

        nodesData.forEach(function (node, idx) {
          let label = 'Undefined'
          if (node.name && node.name !== 'undefined') {
            label = strimwidth(node.name, 20) + '\n' + node.title + '\n' + strimwidth(node.label, 20)
          }
          g.setNode(idx, {label})
        })

        nodesData.forEach(function (node, idx) {
          if (node.url) {
            g.setParent(idx, `url-${_.indexOf(urls, node.url)}`)
          }
        })

        this.graphData.forEach(function (o) {
          let sourceIdx = _.findIndex(nodesData, {name: o[sourceFieldName]})
          let targetIdx = _.findIndex(nodesData, {name: o[targetFieldName]})
          let w = 0
          if (minmax[1] - minmax[0] > 0) {
            w = (parseInt(o[countFieldName]) - minmax[0]) / (minmax[1] - minmax[0])
          }
          linksData.push({
            source: sourceIdx,
            target: targetIdx,
            count: o[countFieldName],
            w
          })
          let width = 3 * w + 1
          g.setEdge(sourceIdx, targetIdx, {
            label: o[countFieldName],
            style: `stroke-width: ${width}px;`,
            arrowheadClass: 'arrowhead'
          })
        })

        const render = new DagreD3.render()
        render(inner, g)

        const zoom = d3.zoom().on('zoom', () => {
          inner.attr('transform', d3.event.transform)
        })
        svg.call(zoom)
        const initialScale = 0.75
        svg.call(zoom.transform, d3.zoomIdentity.translate((svg.attr('width') - g.graph().width * initialScale) / 2, 20).scale(initialScale))
        svg.selectAll('g.node').on('click', function (id) {
          // use `this` for element
          self.node = nodesData[id]
        })
      },
      r () {
        this.render()
      }
    }
  }
</script>

<style>
  #graph .node rect {
    stroke: #333;
    fill: #fff;
    stroke-width: 1.5px;
  }

  #graph path {
    stroke: #333;
    fill: none;
    stroke-width: 1.5px;
  }

  #graph .arrowhead {
    stroke: #333;
    fill: #333;
    stroke-width: 1.5px;
  }

  #graph .clusters rect {
    fill: #fff;
    stroke: #333;
    stroke-width: 1.5px;
  }

  .graph-container {
    position: relative;
  }

  .graph-container .node-info {
    position: absolute;
    left: 0;
    bottom: 0;
    padding: 5px;
    background: #fff;
    max-width: 50vw;
    opacity: 0.8;
  }

  .graph-container .node-info .detail {
    max-height: 200px;
    overflow: auto;
  }

  .graph-container .node-info .detail .label {
    font-weight: bold;
  }

  .graph-container .graph-operation {
    position: absolute;
    right: 0;
    bottom: 0;
    padding: 5px;
  }
</style>
