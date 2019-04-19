<template>
  <div>
    <div class="container-fluid graph-container" v-show="isGraph">
      <div id="graph">
        <div v-if="!isLoading" class="text-center">
          Select report
        </div>
        <div v-if="isLoading" class="text-center">
          <b-spinner label="Loading..." variant="primary"/>
        </div>
      </div>
      <div class="node-info m-2" v-if="rawUrlLinks">
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
      <swagger-sample :url-tree="urlTree" v-if="urlTree"></swagger-sample>
    </b-modal>
    <button type="button" class="btn btn-primary m-2" v-b-modal.swagger-sample>Swagger Sample</button>
  </div>
</template>

<script>
  import axios from 'axios'
  import _ from 'lodash'
  import * as d3 from 'd3'
  import * as DagreD3 from 'dagre-d3'
  import {getTree} from '../lib/UrlTree'
  import {getUrls, filterByUrl, mergeSameId, convertUrl, convertUrlForTableData, skipData} from '../lib/GraphUril'
  import url from 'url'
  import NodeDetail from '../components/NodeDetail'
  import StatTable from '../components/StatTable'
  import StatLineChart from '../components/StatLineChart'
  import SwaggerSample from '../components/SwaggerSample'

  const statusPatterns = {
    pageview: /^pageview$/,
    click_widget: /^click_widget.+/,
    click_trivial: /^click_trivial.+/,
    touchstart: /^touchstart_.+/,
    'change-url': /^change-url.+/,
    timer: /^timer_.+/,
    scroll: /^scroll_.+/
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
    components: {StatTable, NodeDetail, StatLineChart, SwaggerSample},
    data () {
      return {
        // graph mode
        isGraph: true,

        // page graph data
        rawGraphData: null,
        graphData: null,

        // table data
        tableData: null,
        summaryTableData: null,
        lineChartFilterUrl: null,

        // selected node
        node: null,

        // filtered statuses
        statuses: _.keys(statusPatterns),
        enabledStatues: _.difference(_.keys(statusPatterns), ['click_trivial', 'timer', 'scroll']),

        // urls
        urls: [],
        rawUrlLinks: null,
        urlLinks: null,
        urlGraph: null,
        urlLinksData: null,

        // selected url (page)
        url: null,

        // swagger
        swaggerDoc: '',
        urlTree: null,

        // UI
        isExpanded: false,
        thresholdCount: 1,
        mergeSameId: true,
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
        if (data.data.meta.version !== 3) {
          console.log('version miss match')
          this.isLoading = false
          return
        }

        this.tableData = convertUrlForTableData(data.data.table, this.swaggerDoc)
        this.summaryTableData = _(this.tableData).groupBy('url').map((d, url) => {
          const scrollCount = _.sumBy(d, 's_count')

          const data = {
            url,
            count: _.sumBy(d, 'count'),
            session_count: _.sumBy(d, 'session_count'),
            user_count: _.sumBy(d, 'user_count'),
            event_count: _.sumBy(d, 'event_count'),
            t_click_count: _.sumBy(d, 't_click_count'),
            w_click_count: _.sumBy(d, 'w_click_count'),
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
        this.rawUrlLinks = data.data.url_links
        this.urls = data.data.urls
        this.url = null

        this.urlTree = getTree(this.urls)

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
          // filter
          this.urlLinks = _.cloneDeep(this.rawUrlLinks)
          this.urlLinks = convertUrl(this.urlLinks, this.swaggerDoc)
          this.urls = getUrls(this.urlLinks)
          const g = new DagreD3.graphlib.Graph({compound: true}).setGraph({}).setDefaultEdgeLabel(function () {
            return {}
          })

          this.urls.forEach((u, idx) => {
            let label = ''
            const parsedUrl = url.parse(u)
            label += parsedUrl.path + '\n'
            const e = _.find(this.urlLinks, {url: u})
            label += strimwidth(e.title, 12)
            g.setNode(idx, {shape: 'ellipse', label: label})
          })

          g.setNode(this.urls.length, {label: 'Undefined', shape: 'ellipse'})

          const minmax = d3.extent(this.urlLinks, function (o) {
            return parseInt(o['count'])
          })

          this.urlLinks.forEach((u) => {
            let p = _.indexOf(this.urls, u.p_url)
            let t = _.indexOf(this.urls, u.url)

            if (p === -1) {
              p = this.urls.length
            }
            if (t === -1) {
              t = this.urls.length
            }

            let w = 0
            if (minmax[1] - minmax[0] > 0) {
              w = (parseInt(u.count) - minmax[0]) / (minmax[1] - minmax[0])
            }
            let width = 3 * w + 1
            this.urlLinksData.push({source: p, target: t})
            g.setEdge(p, t, {
              label: u.count,
              style: `stroke-width: ${width}px;`,
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
