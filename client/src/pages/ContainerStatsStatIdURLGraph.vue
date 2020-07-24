<template>
  <div>
    <h2 class="mb-2">URL Graph</h2>
    <div id="graph">
      <div v-if="isLoading" class="text-center">
        Loading..
        <b-spinner label="Loading..." variant="primary"/>
      </div>
    </div>
    <div class="node-info m-2" v-if="rawUrlLinks">
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
  import axios from 'axios'
  import * as d3 from 'd3'
  import * as DagreD3 from 'dagre-d3'
  import {getUrls, convertUrl} from '../lib/GraphUril'
  import url from 'url'

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
    data () {
      return {
        isLoading: false,
        rawUrlLinks: null,
        urls: null,
        urlLinksData: null,
        urlLinks: null,
        urlGraph: null,
        svg: null,
        zoom: null,
        thresholdCount: 1
      }
    },
    computed: {
      svgHeight () {
        return window.innerHeight - 200
      },
      swaggerDoc () {
        return this.$store.state.container.swaggerDoc
      }
    },
    async mounted () {
      await this.$store.dispatch('container/fetchSwaggerDoc', {
        org: this.$route.params.org,
        container: this.$route.params.name
      })
      await this.render()
    },
    methods: {
      r () {
        this.render()
      },
      async render () {
        this.isLoading = true
        const stat = await this.$Amplify.API.get('OTMClientAPI', `/orgs/${this.$route.params.org}/containers/${this.$route.params.name}/stats/${this.$route.params.statid}`)
        if (!stat) {
          this.isLoading = false
          return
        }

        const data = await axios.get(stat.file_url)
        if (data.data.meta.version !== 3) {
          console.log('version miss match')
          this.isLoading = false
          return
        }

        this.rawUrlLinks = data.data.url_links
        this.urls = data.data.urls

        this.isLoading = false

        const cl = d3.select('#graph')
        const width = cl.node().clientWidth
        const height = this.svgHeight
        cl.selectAll('*').remove()
        const svg = cl.append('svg').attr('width', width).attr('height', height)
        const inner = svg.append('g')

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
          label += u.replace(/%7b/gi, '{').replace(/%7d/gi, '}') + '\n'
          const count = _.sumBy(_.filter(this.urlLinks, {url: u}), 'count')
          let labelSize = 5 * (count / maxCount)
          if (labelSize < 1) {
            labelSize = 1
          }
          const e = _.find(this.urlLinks, {url: u})
          label += strimwidth(e ? e.title : '', 12)
          g.setNode(idx, {shape: 'ellipse', label: label, labelStyle: `font-size: ${labelSize}em`})
        })
        g.setNode(this.urls.length, {label: 'Direct', shape: 'ellipse', labelStyle: 'font-size: 5em'})
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
            this.goToEventGraph(this.urls[id])
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
      zoomIn () {
        this.zoom.scaleBy(this.svg.transition().duration(750), 1.3)
      },
      zoomOut () {
        this.zoom.scaleBy(this.svg.transition().duration(750), 1 / 1.3)
      },
      goToEventGraph (url) {
        this.$router.push({name: 'Container-Stats-StatId-URLGraph-URL', params: {...this.$route.params, url}})
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
