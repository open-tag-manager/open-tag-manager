<template>
  <div>
    <div class="container-fluid graph-container" v-show="isGraph">
      <div id="graph">
        <div v-if="!isLoading" class="text-center">
          Select report
        </div>
        <div v-if="isLoading" class="text-center">
          <b-spinner label="Loading..." variant="primary" />
        </div>
      </div>
      <div class="node-info m-2" v-if="graphData">
        <node-detail v-if="node" :node="node"></node-detail>

        <button class="btn btn-primary" v-if="url" @click="back">URL Graph</button>
        <button class="btn btn-primary" v-if="tableData" @click="showTable">Table & Line Chart</button>

        <b-form-group label="Enabled Statuses" class="status-filter">
          <b-form-checkbox-group id="enabled-statuses" v-model="enabledStatues"
                                 :options="statuses" @input="r"></b-form-checkbox-group>
        </b-form-group>

        <b-form-checkbox id="merge-same-id" v-model="mergeSameId" @input="render">Merge same ID</b-form-checkbox>

        <b-form-group label="Threshold Count" horizontal>
          <b-form-input v-model.number="thresholdCount" type="number" required @change="r"></b-form-input>
        </b-form-group>
      </div>

      <div v-if="graphData" class="graph-operation m-2">
        <button class="wide-button btn btn-primary" @click="expand">
          <fa-icon icon="expand"></fa-icon>
        </button>
      </div>
    </div>
    <div v-if="!isGraph" class="p-2">
      <div v-if="lineChartFilterUrl">
        Filtered by: {{lineChartFilterUrl}} <a href="#" @click="lineChartFilterUrl = null">x</a>
      </div>
      <stat-line-chart :data="tableData" :filtered-url="lineChartFilterUrl"></stat-line-chart>
      <div class="table-container">
        <stat-table :data="summaryTableData" @clickGraphUrl="goToUrlGraph"
                    @clickFilterUrl="filterLineChartUrl"></stat-table>
      </div>
      <button class="btn btn-primary" @click="showGraph">Graph</button>
    </div>
    <b-modal id="swagger-sample" title="Swagger Sample" hide-footer>
      <textarea class="form-control" readonly rows="20" v-model="prettifySwaggerSample"></textarea>
    </b-modal>
    <button v-if="swaggerSample" type="button" class="btn btn-primary m-2" v-b-modal.swagger-sample>Swagger Sample</button>
  </div>
</template>

<script>
  import axios from 'axios'
  import _ from 'lodash'
  import * as d3 from 'd3'
  import * as DagreD3 from 'dagre-d3'
  import url from 'url'
  import querystring from 'querystring'
  import NodeDetail from '../components/NodeDetail'
  import StatTable from '../components/StatTable'
  import StatLineChart from '../components/StatLineChart'

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
            return `${parsedUrl.protocol}//${parsedUrl.host}${p}`
          }
        } else {
          return `${parsedUrl.protocol}//${parsedUrl.host}${p}`
        }
      }
    }

    return null
  }

  const findRelatedEdge = (data, edges, skipStatePatterns, results = [], path = []) => {
    for (let e of edges) {
      if (e['p_state'] === e['state']) {
        continue
      }
      let idx = _.findIndex(skipStatePatterns, (p) => {
        return e['p_state'] && e['p_state'].match(p)
      })
      if (idx === -1) {
        results.push(e)
      } else {
        // prevent circular reference
        let si = _.findIndex(path, (pe) => {
          return pe['p_state'] && pe['p_state'] === e['p_state']
        })
        if (si !== -1) {
          continue
        }

        let searchCondition = {}
        searchCondition['state'] = e['p_state']
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
        if (d['p_state'] && d['p_state'].match(pattern)) sourceMatched = true
        if (d['state'] && d['state'].match(pattern)) targetMatched = true
      }
      if (d['count'] < thresholdCount) targetMatched = true
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
        searchCondition['state'] = d['p_state']
        searchCondition.url = d.p_url
        let edges = _.filter(data, searchCondition)
        edges = findRelatedEdge(data, edges, skipStatePatterns)
        for (let e of edges) {
          let searchCondition2 = {}
          searchCondition2['p_state'] = e['p_state']
          searchCondition2['state'] = d['state']
          let existsEdge = _.find(cData, searchCondition2)
          let count = e['count'] > d['count'] ? d['count'] : e['count']
          if (existsEdge) {
            existsEdge['count'] += count
          } else {
            let newEdge = {}
            newEdge['p_state'] = e['p_state']
            newEdge['state'] = d['state']
            newEdge.url = d.url
            newEdge.p_url = d.p_url
            newEdge.title = d.title
            newEdge.label = d.label
            newEdge.xpath = d.xpath
            newEdge.a_id = d.a_id
            newEdge.class = d.class
            newEdge['count'] = count
            cData.push(newEdge)
          }
        }
      }
    }

    // Delete skipped edge
    return _.reject(_.reject(cData, 'sourceSkip'), 'targetSkip')
  }

  const mergeSameId = (data) => {
    const cData = []

    for (let d of data) {
      if (d.deleted) {
        continue
      }

      const filtered = _.filter(data, {url: d.url, p_url: d.p_url, state: d.state, p_state: d.p_state})
      if (filtered.length <= 1) {
        cData.push(d)
      } else {
        let count = 0
        for (let fd of filtered) {
          count += fd.count
          fd.deleted = true
        }

        delete d.deleted
        d.count = count
        cData.push(d)
      }
    }

    return cData
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
      let newUrl = lookupPath(paths, url.parse(d.url)) || d.url
      let newPUrl = lookupPath(paths, url.parse(d.p_url)) || d.p_url

      // remove duplicated record
      const e = _.find(data, {url: newUrl, p_url: newPUrl, state: d.state, p_state: d.p_state, m: true})
      if (e) {
        e.count += d.count
        d.url = null
      } else {
        d.url = newUrl
        d.p_url = newPUrl
        d.m = true
      }
    }

    return _.reject(data, (d) => {
      return d.url === null
    })
  }

  const convertUrlForTableData = (data, swaggerDoc) => {
    const cData = _.cloneDeep(data)
    if (!swaggerDoc) {
      return data
    }

    const paths = JSON.parse(swaggerDoc).paths

    if (!paths) {
      return data
    }
    for (let d of cData) {
      let newUrl = lookupPath(paths, url.parse(d.url)) || d.url
      if (d.url === newUrl) {
        continue
      }
      d.url = newUrl
    }

    return cData
  }
  const strimwidth = function (text, size) {
    if (!text) {
      return ''
    }
    if (text.length < size) {
      return text
    }
    return text.replace(/[\n\r]/g, '').substr(0, size) + '...'
  }

  export default {
    components: {StatTable, NodeDetail, StatLineChart},
    data () {
      return {
        isGraph: true,
        graphData: null,
        rawGraphData: null,
        tableData: null,
        summaryTableData: null,
        swaggerSample: null,
        lineChartFilterUrl: null,
        node: null,
        statuses: _.keys(statusPatterns),
        enabledStatues: _.difference(_.keys(statusPatterns), ['click_trivial', 'timer', 'scroll']),
        isExpanded: false,
        urls: [],
        url: null,
        thresholdCount: 1,
        swaggerDoc: '',
        mergeSameId: true,
        urlGraph: null,
        urlLinksData: null,
        isLoading: false
      }
    },
    computed: {
      svgHeight () {
        if (this.isExpanded) {
          return window.innerHeight - 60
        } else {
          return 400
        }
      },
      prettifySwaggerSample () {
        return JSON.stringify(this.swaggerSample, null, 2)
      }
    },
    async created () {
      await this.getSwaggerDoc()
      await this.renderGraph()
    },
    methods: {
      async renderGraph () {
        this.isLoading = true
        const stats = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.$route.params.name}/stats`)
        const stat = _.find(stats, {key: this.$route.params.statid})
        if (!stat) {
          return
        }

        const data = await axios.get(stat.url)
        this.rawGraphData = data.data.result
        this.tableData = convertUrlForTableData(data.data.table, this.swaggerDoc)
        this.swaggerSample = data.data.swagger_sample
        this.summaryTableData = _(this.tableData).groupBy('url').map((d, url) => {
          const scrollCount = _.sumBy(d, 's_count')

          const data = {
            url,
            count: _.sumBy(d, 'count'),
            session_count: _.sumBy(d, 'session_count'),
            user_count: _.sumBy(d, 'user_count'),
            avg_scroll_y: null,
            max_scroll_y: null
          }

          if (scrollCount > 0) {
            data.avg_scroll_y = _.reduce(d, (result, o) => {
              if (!o.s_count) {
                return result
              }

              result += o.avg_scroll_y * o.s_count
              return result
            }, 0) / scrollCount
            data.max_scroll_y = _.maxBy(d, 'max_scroll_y').max_scroll_y
          }

          return data
        }).value()

        /*
        this.rawGraphData = [
          {count: 100, label: 'hello', state: 'pageview', p_state: null, url: 'urlA', p_url: null, xpath: ''},
          {count: 50, label: 'hello', state: 'click_widget_a', p_state: 'pageview', url: 'urlA', p_url: 'urlA'},
          {count: 30, label: 'hello', state: 'pageview', p_state: 'click_widget_a', url: 'urlB', p_url: 'urlA'}
        ]
        */
        this.node = null
        this.urls = getUrls(this.rawGraphData)
        this.url = null
        this.render()
        this.isLoading = false
      },
      async getSwaggerDoc () {
        const data = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.$route.params.name}/swagger_doc`)
        this.swaggerDoc = JSON.stringify(data)
      },
      expand () {
        const cl = d3.select('#graph')
        const svg = cl.select('#graph svg')
        this.isExpanded = !this.isExpanded
        svg.attr('height', this.svgHeight)
      },
      filter () {
        this.graphData = _.cloneDeep(this.rawGraphData)

        // -- data filter process
        // 1. url reformat
        this.graphData = convertUrl(this.graphData, this.swaggerDoc)

        // 2. skip data
        this.graphData = skipData(this.graphData, _.values(_.pick(statusPatterns, _.difference(this.statuses, this.enabledStatues))), this.thresholdCount)

        // 3. merge same id data
        if (this.mergeSameId) {
          this.graphData = mergeSameId(this.graphData)
        }

        // 4. filter by url
        this.urls = getUrls(this.graphData)
      },
      renderUrls () {
        console.log('render URLs')

        const cl = d3.select('#graph')
        const width = cl.node().clientWidth
        const height = this.svgHeight
        cl.selectAll('*').remove()
        const svg = cl.append('svg').attr('width', width).attr('height', height)
        const inner = svg.append('g')

        if (!this.urlGraph) {
          this.urlLinksData = []
          this.filter()
          const g = new DagreD3.graphlib.Graph({compound: true}).setGraph({}).setDefaultEdgeLabel(function () {
            return {}
          })

          this.urls.forEach((u, idx) => {
            let label = ''
            const parsedUrl = url.parse(u)
            label += parsedUrl.path + '\n'
            const e = _.find(this.graphData, {url: u})
            label += strimwidth(e.title)
            g.setNode(idx, {shape: 'ellipse', label: label})
          })

          const h = {}
          const urlLinks = this.graphData.reduce(function (r, o) {
            let key = `${o.url}-${o.p_url}`

            if (!h[key]) {
              h[key] = Object.assign({}, o)
              r.push(h[key])
            } else {
              h[key].count += o.count
            }

            return r
          }, [])

          g.setNode(this.urls.length, {label: 'Undefined', shape: 'ellipse'})

          urlLinks.forEach((u) => {
            let p = _.indexOf(this.urls, u.p_url)
            let t = _.indexOf(this.urls, u.url)

            if (p === -1) {
              p = this.urls.length
            }
            if (t === -1) {
              t = this.urls.length
            }
            this.urlLinksData.push({source: p, target: t})
            g.setEdge(p, t, {
              label: u.count,
              arrowheadClass: 'arrowhead',
              curve: d3.curveBasis
            })
          })
          this.urlGraph = g
        }

        const render = new DagreD3.render()
        render(inner, this.urlGraph)

        const zoom = d3.zoom().on('zoom', () => {
          inner.attr('transform', d3.event.transform)
        })
        svg.call(zoom)
        const initialScale = 0.75
        svg.call(zoom.transform, d3.zoomIdentity.translate((svg.attr('width') - this.urlGraph.graph().width * initialScale) / 2, 20).scale(initialScale))

        svg.selectAll('g.node').on('click', (id) => {
          if (id !== this.urls.length) {
            this.url = this.urls[id]
            this.render()
          }
        })
        svg.selectAll('g.node').on('mouseover', (id) => {
          d3.select(svg.selectAll('g.node').nodes()[id]).classed('hover', true)
          const keys = _.keys(_.pickBy(this.urlLinksData, {source: parseInt(id)})).concat(_.keys(_.pickBy(this.urlLinksData, {target: parseInt(id)})))
          const edgePaths = svg.selectAll('g.edgePath').nodes()
          const edgeLabels = svg.selectAll('g.edgeLabel').nodes()
          for (let key of keys) {
            d3.select(edgePaths[parseInt(key)]).classed('hover', true)
            d3.select(edgeLabels[parseInt(key)]).classed('hover', true)
          }
        })
        svg.selectAll('g.node').on('mouseout', (id) => {
          d3.select(svg.selectAll('g.node').nodes()[id]).classed('hover', false)
          const keys = _.keys(_.pickBy(this.urlLinksData, {source: parseInt(id)})).concat(_.keys(_.pickBy(this.urlLinksData, {target: parseInt(id)})))
          const edgePaths = svg.selectAll('g.edgePath').nodes()
          const edgeLabels = svg.selectAll('g.edgeLabel').nodes()
          for (let key of keys) {
            d3.select(edgePaths[parseInt(key)]).classed('hover', false)
            d3.select(edgeLabels[parseInt(key)]).classed('hover', false)
          }
        })
      },
      back () {
        this.url = null
        this.node = null
        this.render()
      },
      showTable () {
        this.lineChartFilterUrl = this.url
        this.isGraph = false
      },
      showGraph () {
        this.isGraph = true
      },
      goToUrlGraph (url) {
        this.url = url
        this.isGraph = true
        setTimeout(() => {
          this.render()
        }, 500)
      },
      filterLineChartUrl (url) {
        this.lineChartFilterUrl = url
      },
      render () {
        if (!this.url) {
          return this.renderUrls()
        }

        console.log('render')

        this.filter()
        this.graphData = filterByUrl(this.graphData, this.url)

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

        const minmax = d3.extent(this.graphData, function (o) {
          return parseInt(o['count'])
        })

        this.graphData.forEach(function (o) {
          if (!o.label) {
            o.label = ''
          }
          let sourceIdx = _.findIndex(nodesData, {name: o['p_state'], url: o.p_url})
          if (sourceIdx === -1) {
            nodesData.push({name: o['p_state'], url: o.p_url})
          }
          let targetIdx = _.findIndex(nodesData, {name: o['state'], url: o.url})
          if (targetIdx === -1) {
            nodesData.push({name: o['state'], url: o.url})
          }
          targetIdx = _.findIndex(nodesData, {name: o['state'], url: o.url})

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
            let style = 'fill:' + color(url) + ';rx:5px;ry:5px'
            if (url === this.url) {
              style += ';stroke-width:5px'
            }
            g.setNode(`url-${idx}`, {label: url, clusterLabelPos: 'top', style})
          }
        })

        nodesData.forEach(function (node, idx) {
          let label = 'Undefined'
          if (node.name && node.name !== 'undefined') {
            label = strimwidth(node.name, 20) + '\n' + node.title + '\n' + strimwidth(node.label, 20)
          }
          g.setNode(idx, {shape: 'ellipse', label})
        })

        nodesData.forEach(function (node, idx) {
          if (node.url) {
            g.setParent(idx, `url-${_.indexOf(urls, node.url)}`)
          }
        })

        this.graphData.forEach(function (o) {
          let sourceIdx = _.findIndex(nodesData, {name: o['p_state'], url: o.p_url})
          let targetIdx = _.findIndex(nodesData, {name: o['state'], url: o.url})

          if (sourceIdx === -1 || targetIdx === -1) {
            return
          }

          let w = 0
          if (minmax[1] - minmax[0] > 0) {
            w = (parseInt(o['count']) - minmax[0]) / (minmax[1] - minmax[0])
          }
          linksData.push({
            source: sourceIdx,
            target: targetIdx,
            count: o['count'],
            w
          })
          let width = 3 * w + 1
          g.setEdge(sourceIdx, targetIdx, {
            label: o['count'],
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

        svg.selectAll('g.node').on('mouseover', (id) => {
          d3.select(svg.selectAll('g.node').nodes()[id]).classed('hover', true)
          const keys = _.keys(_.pickBy(linksData, {source: parseInt(id)})).concat(_.keys(_.pickBy(linksData, {target: parseInt(id)})))
          const edgePaths = svg.selectAll('g.edgePath').nodes()
          const edgeLabels = svg.selectAll('g.edgeLabel').nodes()
          for (let key of keys) {
            d3.select(edgePaths[parseInt(key)]).classed('hover', true)
            d3.select(edgeLabels[parseInt(key)]).classed('hover', true)
          }
        })
        svg.selectAll('g.node').on('mouseout', (id) => {
          d3.select(svg.selectAll('g.node').nodes()[id]).classed('hover', false)
          const keys = _.keys(_.pickBy(linksData, {source: parseInt(id)})).concat(_.keys(_.pickBy(linksData, {target: parseInt(id)})))
          const edgePaths = svg.selectAll('g.edgePath').nodes()
          const edgeLabels = svg.selectAll('g.edgeLabel').nodes()
          for (let key of keys) {
            d3.select(edgePaths[parseInt(key)]).classed('hover', false)
            d3.select(edgeLabels[parseInt(key)]).classed('hover', false)
          }
        })
        svg.selectAll('g.node').on('click', (id) => {
          this.node = nodesData[id]
        })
        svg.selectAll('g.cluster').on('click', (id) => {
          const match = id.match(/url-(\d+)/)
          const u = urls[parseInt(match[1])]
          if (u !== this.url) {
            this.url = u
            this.render()
          }
        })
      },
      r () {
        this.urlGraph = null
        this.render()
      }
    }
  }
</script>

<style scoped>
  .graph-container {
    position: relative;
  }

  .table-container {
    height: 300px;
    overflow: scroll;
  }

  .node-info {
    position: absolute;
    left: 0;
    bottom: 0;
    background: #fff;
    max-width: 50vw;
    opacity: 0.8;
  }

  .graph-operation {
    position: absolute;
    right: 0;
    bottom: 0;
  }
</style>
