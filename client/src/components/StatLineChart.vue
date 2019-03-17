<template>
  <div id="line-chart">
  </div>
</template>

<script>
  import * as d3 from 'd3'
  import _ from 'lodash'

  export default {
    props: {
      data: {
        type: Array,
        required: true
      }
    },
    methods: {
      render () {
        let data = _.cloneDeep(this.data)
        data = _(data).groupBy('datetime').map((d, datetime) => {
          const scrollCount = _.sumBy(d, 's_count')

          const data = {
            datetime: new Date(datetime),
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

        const cl = d3.select('#line-chart')
        const width = cl.node().clientWidth
        const height = 200
        const margin = {top: 30, bottom: 60, right: 30, left: 60}
        cl.selectAll('*').remove()
        const svg = cl.append('svg').attr('width', width).attr('height', height)

        const xScale = d3.scaleTime()
          .domain([d3.min(data.map((d) => { return d.datetime })), d3.max(data.map((d) => { return d.datetime }))])
          .range([margin.left, width - margin.right])
        const yScale = d3.scaleLinear()
          .domain([0, d3.max(data.map((d) => { return d.count }))])
          .range([height - margin.bottom, margin.top])
        const xAxis = d3.axisBottom(xScale).tickFormat(d3.timeFormat('%m/%d %H'))
        const yAxis = d3.axisLeft(yScale).ticks(5)

        svg.append('g')
          .attr('transform', 'translate(' + 0 + ',' + (height - margin.bottom) + ')')
          .call(xAxis)
          .append('text')
          .attr('fill', 'black')
          .attr('x', (width - margin.left - margin.right) / 2 + margin.left)
          .attr('y', 35)
          .attr('text-anchor', 'middle')
          .attr('font-size', '10pt')
          .attr('font-weight', 'bold')
          .text('Time')

        svg.append('g')
          .attr('transform', 'translate(' + margin.left + ',' + 0 + ')')
          .call(yAxis)
          .append('text')
          .attr('fill', 'black')
          .attr('text-anchor', 'middle')
          .attr('x', -(height - margin.top - margin.bottom) / 2 - margin.top)
          .attr('y', -35)
          .attr('transform', 'rotate(-90)')
          .attr('font-weight', 'bold')
          .attr('font-size', '10pt')
          .text('count')

        svg.append('path').datum(data)
          .attr('fill', 'none')
          .attr('stroke', 'steelblue')
          .attr('stroke-width', 1.5)
          .attr('d', d3.line()
            .x((d) => { return xScale(new Date(d.datetime)) })
            .y((d) => { return yScale(d.count) })
          )
      }
    },
    mounted () {
      this.render()
    }
  }
</script>
