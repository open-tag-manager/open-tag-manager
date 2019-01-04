<template>
  <div class="container-fluid graph-container">
    <div id="graph">
      <div>
        Select report
      </div>
    </div>
    <div class="node-info" v-if="graphData">
      <node-detail v-if="node" :node="node"></node-detail>

      <b-form-select v-model="url" :options="urls" @input="r"></b-form-select>

      <b-form-group label="Enabled Statuses" class="status-filter">
        <b-form-checkbox-group id="enabled-statuses" v-model="enabledStatues"
                               :options="statuses" @input="r"></b-form-checkbox-group>
      </b-form-group>

      <b-form-group label="Threshold Count" horizontal>
        <b-form-input v-model.number="thresholdCount" type="number" required @change="r"></b-form-input>
      </b-form-group>
    </div>

    <div v-if="graphData" class="graph-operation">
      <button class="wide-button btn btn-primary" @click="expand">
        <fa-icon icon="expand"></fa-icon>
      </button>
    </div>
  </div>
</template>

<script>
  import api from '../api'
  import axios from 'axios'
  import _ from 'lodash'
  import * as d3 from 'd3'
  import * as DagreD3 from 'dagre-d3'
  import url from 'url'
  import querystring from 'querystring'
  import NodeDetail from '../components/NodeDetail'

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

  const lookupPath = (paths, parsedUrl) => {
    if (!parsedUrl.path) {
      return null
    }

    let path = parsedUrl.path
    if (parsedUrl.hash) {
      const match = parsedUrl.hash.match(/^#!(\/.*)/)
      if (match) {
        const hashUrl = url.parse(match[1])
        path = hashUrl.path
      }
    }

    const targetUrl = url.parse(path)
    const targetQs = querystring.parse(targetUrl.query)

    for (let p in paths) {
      const u = url.parse(p)
      const r = new RegExp('^' + u.pathname.replace(/{[^}]*}/g, '[^/]*') + '$')

      if (r.exec(targetUrl.pathname)) {
        // match pathname
        if (u.query) {
          let queryMatch = true
          const qs = querystring.parse(u.query)
          for (let qd in qs) {
            const qr = new RegExp('^' + qs[qd].replace(/{[^}]*}/g, '[^/]*') + '$')
            if (!qr.exec(targetQs[qd])) {
              queryMatch = false
              break
            }
          }
          if (queryMatch) {
            return p
          }
        } else {
          return p
        }
      }
    }
    return null
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
        searchCondition.url = e.p_url
        let deepEdges = _.filter(data, searchCondition)
        path.push(e)
        findRelatedEdge(data, deepEdges, skipStatePatterns, results, path)
      }
    }

    return results
  }

  const getUrls = (data) => {
    const urls = []
    for (let d of data) {
      if (d.url && !_.includes(urls, d.url)) {
        urls.push(d.url)
      }
    }
    return urls
  }

  const filterByUrl = (data, url) => {
    const newData = _.filter(data, {url})

    _.each(data, (d) => {
      if (d.url === url) {
        return
      }

      if (d.p_url === url) {
        newData.push(d)
      }
    })

    return newData
  }

  const skipData = (data, skipStatePatterns = [], thresholdCount) => {
    const cData = _.cloneDeep(data)
    // Mark as skip
    for (let d of cData) {
      let sourceMatched = false
      let targetMatched = false
      for (let pattern of skipStatePatterns) {
        if (d[sourceFieldName] && d[sourceFieldName].match(pattern)) sourceMatched = true
        if (d[targetFieldName] && d[targetFieldName].match(pattern)) targetMatched = true
      }
      if (d[countFieldName] < thresholdCount) targetMatched = true
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
        searchCondition.url = d.p_url
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
            newEdge.p_url = d.p_url
            newEdge.title = d.title
            newEdge.label = d.label
            newEdge.xpath = d.xpath
            newEdge.a_id = d.a_id
            newEdge.class = d.class
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

    const paths = JSON.parse(swaggerDoc).paths

    if (!paths) {
      return data
    }

    for (let d of data) {
      d.url = lookupPath(paths, url.parse(d.url)) || d.url
      d.p_url = lookupPath(paths, url.parse(d.p_url)) || d.p_url

      // remove duplicated record
      const e = _.find(data, {url: d.url, p_url: d.p_url, state: d.state, p_state: d.p_state})
      if (e) {
        e.count += d.count
        d.url = null
      }
    }

    return _.reject(data, (d) => {
      return d.url === null
    })
  }

  export default {
    components: {NodeDetail},
    data () {
      return {
        graphData: null,
        rawGraphData: null,
        node: null,
        statuses: _.keys(statusPatterns),
        enabledStatues: _.difference(_.keys(statusPatterns), ['click_trivial', 'timer', 'scroll']),
        isExpanded: false,
        urls: [],
        url: null,
        thresholdCount: 1,
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
      await this.getSwaggerDoc()
      await this.renderGraph()
    },
    methods: {
      async renderGraph () {
        const statsData = await api(this.$store).get(`containers/${this.$route.params.name}/stats`)
        const stats = statsData.data
        const stat = _.find(stats, {key: this.$route.params.statid})
        if (!stat) {
          return
        }

        const data = await axios.get(stat.url)
        this.rawGraphData = data.data.result

        this.node = null
        this.urls = getUrls(this.rawGraphData)
        if (this.urls.length === 0) {
          return
        }
        this.url = this.urls[0]
        this.render()
      },
      async getSwaggerDoc () {
        const data = await api(this.$store).get(`containers/${this.$route.params.name}/swagger_doc`)
        this.swaggerDoc = JSON.stringify(data.data)
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

        // -- data filter process
        // 1. url reformat
        this.graphData = convertUrl(this.graphData, this.swaggerDoc)

        // 2. skip data
        this.graphData = skipData(this.graphData, _.values(_.pick(statusPatterns, _.difference(this.statuses, this.enabledStatues))), this.thresholdCount)

        // 3. filter by url
        this.urls = getUrls(this.graphData)
        this.graphData = filterByUrl(this.graphData, this.url)
        // -- data filter process

        const cl = d3.select('#graph')
        const width = cl.node().clientWidth
        const height = this.svgHeight
        cl.selectAll('*').remove()
        const svg = cl.append('svg').attr('width', width).attr('height', height)
        const inner = svg.append('g')
        const g = new DagreD3.graphlib.Graph({compound: true}).setGraph({}).setDefaultEdgeLabel(function () {
          return {}
        })

        if (this.graphData.length === 0) {
          console.log('no data to render')
          return
        }

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
          let sourceIdx = _.findIndex(nodesData, {name: o[sourceFieldName], url: o.p_url})
          if (sourceIdx === -1) {
            nodesData.push({name: o[sourceFieldName], url: o.p_url})
          }
          let targetIdx = _.findIndex(nodesData, {name: o[targetFieldName], url: o.url})
          if (targetIdx === -1) {
            nodesData.push({name: o[targetFieldName], url: o.url})
          }
          targetIdx = _.findIndex(nodesData, {name: o[targetFieldName], url: o.url})

          if (o.url) {
            if (_.indexOf(urls, o.url) === -1) {
              urls.push(o.url)
            }
          }
          if (o.p_url) {
            if (_.indexOf(urls, o.p_url) === -1) {
              urls.push(o.p_url)
            }
          }

          nodesData[targetIdx].url = o.url
          nodesData[targetIdx].title = o.title
          nodesData[targetIdx].label = o.label
          nodesData[targetIdx].xpath = o.xpath
          nodesData[targetIdx].a_id = o.a_id
          nodesData[targetIdx].class = o.class
        })

        urls.forEach((url, idx) => {
          if (_.find(nodesData, {url})) {
            let style = 'fill:' + color(url)
            if (url === this.url) {
              style += ';stroke-width:10px'
            }
            g.setNode(`url-${idx}`, {label: url, clusterLabelPos: 'top', style})
          }
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
          let sourceIdx = _.findIndex(nodesData, {name: o[sourceFieldName], url: o.p_url})
          let targetIdx = _.findIndex(nodesData, {name: o[targetFieldName], url: o.url})

          if (sourceIdx === -1 || targetIdx === -1) {
            return
          }

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
            arrowheadClass: 'arrowhead',
            curve: d3.curveBasis
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
