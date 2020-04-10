<template>
  <div>
    <div class="d-flex">
      <b-button variant="link" @click="back">&lt;</b-button>
      <h2 class="mb-2">Event Graph</h2>
    </div>
    <div id="graph">
      <div v-if="isLoading" class="text-center">
        Loading..
        <b-spinner label="Loading..." variant="primary"/>
      </div>
    </div>
    <div class="node-info m-2" v-if="svg">
      <node-detail v-if="node" :node="node" />

      <b-form-group label="Enabled Statuses" class="status-filter">
        <b-form-checkbox-group id="enabled-statuses" v-model="enabledStatues"
                               :options="statuses" @input="r"></b-form-checkbox-group>
      </b-form-group>
      <b-form-checkbox id="merge-same-id" v-model="mergeSameId" @input="r">Merge same ID</b-form-checkbox>
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
</template>

<script>
  import _ from 'lodash'
  import * as d3 from 'd3'
  import * as DagreD3 from 'dagre-d3'
  import NodeDetail from '../components/NodeDetail'
  import {mergeSameId, convertUrl, skipData} from '../lib/GraphUril'

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
    components: {NodeDetail},
    data () {
      return {
        isLoading: false,
        url: this.$route.params.url,
        rawGraphData: null,
        thresholdCount: 1,
        mergeSameId: true,
        node: null,
        svg: null,
        zoom: null,
        statuses: _.keys(statusPatterns),
        enabledStatues: _.difference(_.keys(statusPatterns), ['click_trivial', 'timer', 'scroll'])
      }
    },
    async mounted () {
      await this.render()
    },
    computed: {
      svgHeight () {
        return window.innerHeight - 200
      },
      swaggerDoc () {
        return this.$store.state.container.swaggerDoc
      }
    },
    methods: {
      r () {
        this.render()
      },
      async render () {
        this.isLoading = true
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
          let label = 'Origin'
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
            this.goToAnotherUrl(u)
          }
        })
        this.svg = svg
        this.zoom = zoom
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
      back () {
        this.$router.push({name: 'Container-Stats-StatId-URLGraph'})
      },
      zoomIn () {
        this.zoom.scaleBy(this.svg.transition().duration(750), 1.3)
      },
      zoomOut () {
        this.zoom.scaleBy(this.svg.transition().duration(750), 1 / 1.3)
      },
      goToAnotherUrl (u) {
        this.$router.push({params: {...this.$route.params, url: u}})
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
</style>
