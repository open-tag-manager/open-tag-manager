<template>
  <div :key="$router.fullPath">
    <button type="button" class="btn btn-primary m-2" v-b-modal.swagger-sample>Swagger Sample</button>
    <div class="graph-container" v-show="mode === 'graph'">
      <div id="graph">
        <div v-if="isLoading" class="text-center">
          <b-spinner label="Loading..." variant="primary"/>
        </div>
      </div>
      <div class="node-info m-2" v-if="rawUrlLinks">
        <node-detail v-if="node" :node="node">
          <button class="btn btn-primary btn-sm" @click="showEvent(node)">Event Table</button>
        </node-detail>

        <button class="btn btn-primary" v-if="url" @click="back">URL Graph</button>
        <button class="btn btn-primary" v-if="tableData" @click="showTable">Table &amp; Line Chart</button>
        <button class="btn btn-primary" @click="showEvent()">Event Table</button>

        <b-form-group label="Enabled Statuses" class="status-filter">
          <b-form-checkbox-group id="enabled-statuses" v-model="enabledStatues"
                                 :options="statuses" @input="r"></b-form-checkbox-group>
        </b-form-group>

        <b-form-checkbox id="merge-same-id" v-model="mergeSameId" @input="render">Merge same ID</b-form-checkbox>

        <b-form-group label="Threshold Count" horizontal>
          <b-form-input v-model.number="thresholdCount" type="number" required @change="r"></b-form-input>
        </b-form-group>
      </div>
      <div class="rb-menu">
        <div class="btn-group" role="group">
          <button id="zoom-in-button" @click="zoomIn" type="button" class="btn btn-primary">+</button>
          <button id="zoom-out-button" @click="zoomOut" type="button" class="btn btn-primary">-</button>
        </div>
      </div>
    </div>
    <div v-if="mode === 'table'" class="p-2">
      <div class="mb-2">
        <button class="btn btn-primary" @click="showGraph">Graph</button>
        <button class="btn btn-primary" @click="showEvent()">Event Table</button>
      </div>
      <div v-if="lineChartFilterUrl">
        Filtered by: {{lineChartFilterUrl}} <a href="#" @click="lineChartFilterUrl = null">x</a>
      </div>
      <stat-line-chart :data="tableData" :filtered-url="lineChartFilterUrl"></stat-line-chart>
      <div class="table-container">
        <stat-table :data="summaryTableData" @clickGraphUrl="goToUrlGraph"
                    @clickFilterUrl="filterLineChartUrl"></stat-table>
      </div>

    </div>
    <div v-if="mode === 'event'" class="p-2">
      <div class="mb-2">
        <button class="btn btn-primary" @click="showGraph">Graph</button>
        <button class="btn btn-primary" v-if="tableData" @click="showTable">Table &amp; Line Chart</button>
      </div>
      <div class="table-container">
        <div v-if="eventTableFilterState">
          Filtered by: {{eventTableFilterState}} <a href="#" @click="eventTableFilterState = null">x</a>
        </div>
        <b-form-group label="Enabled Statuses" class="status-filter" v-else>
          <b-form-checkbox-group id="enabled-statuses-event" v-model="enabledStatues"
                                 :options="statuses"></b-form-checkbox-group>
        </b-form-group>
        <event-table :data="eventTableData" :filter-state="eventTableFilterState" :filter-states="enabledStatues">
        </event-table>
      </div>
    </div>
    <b-modal id="swagger-sample" title="Swagger Sample" hide-footer ref="swaggerSampleModal">
      <swagger-sample :url-tree="urlTree" :original-url-tree="originalUrlTree" v-if="urlTree"
                      @save="saveSwaggerSample"></swagger-sample>
    </b-modal>
  </div>
</template>

<script>
  import axios from 'axios'
  import _ from 'lodash'
  import * as d3 from 'd3'
  import * as DagreD3 from 'dagre-d3'
  import {getTree} from '../lib/UrlTree'
  import {getUrls, mergeSameId, convertUrl, convertUrlForTableData, skipData} from '../lib/GraphUril'
  import url from 'url'
  import NodeDetail from '../components/NodeDetail'
  import StatTable from '../components/StatTable'
  import StatLineChart from '../components/StatLineChart'
  import SwaggerSample from '../components/SwaggerSample'
  import EventTable from '../components/EventTable'

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
    components: {StatTable, NodeDetail, StatLineChart, SwaggerSample, EventTable},
    data () {
      return {
        // graph mode
        mode: 'graph',

        // page graph data
        rawGraphData: null,
        graphData: null,

        // table data
        tableData: null,
        summaryTableData: null,
        lineChartFilterUrl: null,

        // event table data
        rawEventTableData: null,
        eventTableData: null,
        eventTableFilterState: null,

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
        urlTree: null,
        originalUrlTree: null,

        // UI
        thresholdCount: 1,
        mergeSameId: true,
        isLoading: false,

        svg: null,
        zoom: null
      }
    },
    computed: {
      svgHeight () {
        return window.innerHeight - 120
      },
      swaggerDoc () {
        return this.$store.state.container.swaggerDoc
      },
      swaggerDocRevision () {
        return this.$store.state.container.swaggerDocRevision
      }
    },
    watch: {
      async swaggerDocRevision () {
        await this.renderGraph()
      }
    },
    async mounted () {
      await this.$store.dispatch('container/fetchSwaggerDoc', {
        org: this.$route.params.org,
        container: this.$route.params.name
      })
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
          const pltCount = _.sumBy(d, 'plt_count')

          const data = {
            url,
            count: _.sumBy(d, 'count'),
            session_count: _.sumBy(d, 'session_count'),
            user_count: _.sumBy(d, 'user_count'),
            event_count: _.sumBy(d, 'event_count'),
            t_click_count: _.sumBy(d, 't_click_count'),
            w_click_count: _.sumBy(d, 'w_click_count'),
            avg_scroll_y: null,
            max_scroll_y: null,
            avg_plt: null,
            max_plt: null
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

          if (pltCount > 0) {
            data.avg_plt = _.reduce(d, (result, o) => {
              if (!o.plt_count) {
                return result
              }

              result += o.avg_plt * o.plt_count
              return result
            }, 0) / pltCount
            data.max_plt = _.maxBy(d, 'max_plt').max_plt
          }

          return data
        }).value()

        this.node = null
        this.rawUrlLinks = data.data.url_links
        this.urls = data.data.urls

        /*
        this.rawUrlLinks = [
          {count: 100, url: 'https://example.com/', p_url: 'undefined', title: 'Home'},
          {count: 100, url: 'https://example.com/1', p_url: 'https://example.com/', title: '1'},
          {count: 100, url: 'https://example.com/2', p_url: 'https://example.com/', title: '1'},
          {count: 100, url: 'https://example.com/1/hogehoge', p_url: 'https://example.com/1', title: '1-2'}
        ]
        this.urls = ['https://example.com/', 'https://example.com/1', 'https://example.com/2', 'https://example.com/1/hogehoge']
         */

        this.url = null
        this.urlTree = getTree(this.urls, this.$store.getters['container/getSwaggetDocPaths'])
        this.originalUrlTree = getTree(this.urls)

        await this.render()
        this.isLoading = false
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
          this.urlLinks = _.filter(this.urlLinks, (d) => {
            return d.count >= this.thresholdCount
          })
          if (this.swaggerDoc) {
            const swaggerPaths = JSON.parse(this.swaggerDoc).paths

            if (swaggerPaths) {
              this.urlLinks = _.filter(this.urlLinks, (d) => {
                if (d.url) {
                  const parsedUrl = url.parse(d.url)
                  const sObj = swaggerPaths[parsedUrl.path.replace(/%7b/gi, '{').replace(/%7d/gi, '}')]
                  if (sObj && sObj.otmHideNode) {
                    return false
                  }
                }

                if (d.p_url) {
                  const parsedUrl = url.parse(d.p_url)
                  const sObj = swaggerPaths[parsedUrl.path.replace(/%7b/gi, '{').replace(/%7d/gi, '}')]
                  if (sObj && sObj.otmHideNode) {
                    return false
                  }
                }

                return true
              })
            }
          }
          this.urls = getUrls(this.urlLinks)
          const g = new DagreD3.graphlib.Graph({compound: true}).setGraph({}).setDefaultEdgeLabel(function () {
            return {}
          })
          const maxCount = _.max(_.values(_.groupBy(this.urlLinks, 'url')).map((d) => {
            return _.sumBy(d, 'count')
          }))
          this.urls.forEach((u, idx) => {
            let label = ''
            const parsedUrl = url.parse(u)
            label += parsedUrl.path.replace(/%7b/gi, '{').replace(/%7d/gi, '}') + '\n'
            const e = _.find(this.urlLinks, {url: u})

            const count = _.sumBy(_.filter(this.urlLinks, {url: u}), 'count')
            let labelSize = 10 * (count / maxCount)
            if (labelSize < 1) {
              labelSize = 1
            }

            label += strimwidth(e.title, 12)
            g.setNode(idx, {shape: 'ellipse', label: label, labelStyle: `font-size: ${labelSize}em`})
          })

          g.setNode(this.urls.length, {label: 'Undefined', shape: 'ellipse', labelStyle: 'font-size: 5em'})

          this.urlLinks.forEach((u) => {
            let p = _.indexOf(this.urls, u.p_url)
            let t = _.indexOf(this.urls, u.url)

            if (p === -1) {
              p = this.urls.length
            }
            if (t === -1) {
              t = this.urls.length
            }

            let width = 2 * Math.log10(u.count) + 1
            this.urlLinksData.push({source: p, target: t, count: u.count})
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

        this.svg = svg
        this.zoom = zoom
      },
      back () {
        this.url = null
        this.node = null
        this.render()
      },
      showTable () {
        this.lineChartFilterUrl = this.url
        this.mode = 'table'
      },
      showGraph () {
        this.mode = 'graph'
      },
      async showEvent (node = null) {
        if (!this.rawEventTableData) {
          const statId = this.$route.params.statid
          const file = statId.match(/\/([^/]+\.json)$/)[1]
          const data = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.$route.params.name}/stats/${encodeURIComponent(file)}/events`)
          this.rawEventTableData = data
        }
        if (!this.rawEventTableData) {
          return null
        }

        if (node) {
          this.eventTableFilterState = node.name
        } else {
          this.eventTableFilterState = null
        }
        let eventTableData = convertUrlForTableData(this.rawEventTableData.event_table)
        eventTableData = _(eventTableData).groupBy((d) => {
          return `${d.url}-${d.state}`
        }).map((d) => {
          const data = d[0]
          data['count'] = _.sumBy(d, 'count')
          return data
        }).value()

        this.eventTableData = eventTableData
        this.mode = 'event'
      },
      goToUrlGraph (url) {
        this.url = url
        this.mode = 'graph'
        setTimeout(() => {
          this.render()
        }, 500)
      },
      filterLineChartUrl (url) {
        this.lineChartFilterUrl = url
      },
      async render () {
        if (!this.url) {
          this.renderUrls()
          return
        }

        console.log('render')

        const statId = this.$route.params.statid
        const file = statId.match(/\/([^/]+\.json)$/)[1]
        const data = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.$route.params.name}/stats/${encodeURIComponent(file)}`, {
          queryStringParameters: {
            url_filter: this.url
          }
        })
        this.rawGraphData = data.result

        this.filter()

        if (this.graphData.length >= 2000 && this.thresholdCount < 5) {
          console.log('too many data')
          this.urlGraph = null
          this.thresholdCount = 5
          this.filter()
        }

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

        this.graphData.forEach(function (o) {
          if (!o.label) {
            o.label = ''
          }
          let sourceIdx = _.findIndex(nodesData, {name: o['p_state'], url: o.p_url})
          if (sourceIdx === -1) {
            nodesData.push({name: o['p_state'], url: o.p_url, title: o.p_title, label: o.p_label, xpath: o.p_xpath, a_id: o.p_a_id, class: o.p_class})
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
          const node = _.find(nodesData, {url})
          if (node) {
            let style = 'fill:' + color(url) + ';rx:5px;ry:5px'
            if (url === this.url) {
              style += ';stroke-width:5px'
            }
            let label = `${url}\n${strimwidth(node.title, 20)}`
            g.setNode(`url-${idx}`, {label, clusterLabelPos: 'top', style})
          }
        })

        nodesData.forEach(function (node, idx) {
          let label = 'Undefined'
          if (node.name && node.name !== 'undefined') {
            let lCaption = node.label
            if (lCaption) {
              const m = lCaption.match(/\/(.+)$/)
              if (m) {
                lCaption = m[1]
              }
            } else {
              lCaption = node.name
            }

            label = strimwidth(lCaption, 20)
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

          linksData.push({
            source: sourceIdx,
            target: targetIdx,
            count: o['count'],
            w: Math.log10(o.count)
          })
          let width = 2 * Math.log10(o.count) + 1
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
        this.svg = svg
        this.zoom = zoom
      },
      async r () {
        this.urlGraph = null
        await this.render()
      },
      async saveSwaggerSample ({sample}) {
        this.$store.dispatch('container/editSwaggerDoc', {swaggerDoc: JSON.stringify(sample)})
        await this.$store.dispatch('container/saveSwaggerDoc', {
          org: this.$route.params.org,
          container: this.$route.params.name
        })
        this.$refs.swaggerSampleModal.hide()
      },
      zoomIn () {
        this.zoom.scaleBy(this.svg.transition().duration(750), 1.3)
      },
      zoomOut () {
        this.zoom.scaleBy(this.svg.transition().duration(750), 1 / 1.3)
      }
    }
  }
</script>

<style>
  #graph .node rect, #graph .node ellipse {
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

  #graph .node.hover ellipse {
    stroke: #d9534f;
  }

  #graph .edgePath.hover path {
    stroke: #d9534f;
  }

  #graph .edgeLabel.hover {
    color: #d9534f;
  }
</style>

<style scoped>
  .graph-container {
    position: relative;
  }

  .node-info {
    position: absolute;
    left: 0;
    bottom: 0;
    background: #fff;
    max-width: 50vw;
    opacity: 0.8;
  }

  .rb-menu {
    position: absolute;
    right: 20px;
    bottom: 20px;
  }

  .graph-operation {
    position: absolute;
    right: 0;
    bottom: 0;
  }
</style>
