<template>
  <div class="stat-line-chart">
    <div class="line-chart" />
    <v-radio-group v-model="yItem" row>
      <v-radio
        v-for="option in options"
        :key="option.value"
        :label="option.text"
        :value="option.value"
      />
    </v-radio-group>
  </div>
</template>

<script lang="ts">
import { Component, Vue, Prop, Watch } from 'vue-property-decorator'
import { groupBy, sumBy, reduce, maxBy, sortBy } from 'lodash-es'
import { pointer as d3pointer, select as d3select } from 'd3-selection'
import { scaleTime, scaleLinear } from 'd3-scale'
import { bisector as d3bisector, max as d3max, min as d3min } from 'd3-array'
import { axisBottom, axisLeft } from 'd3-axis'
import { timeFormat as d3timeFormat, timeFormat } from 'd3-time-format'
import { line as d3line } from 'd3-shape'
import { IStatDataTable } from '~/utils/api/stat'

/* eslint-disable camelcase */
interface LineChartData {
  datetime: Date
  count: number
  session_count: number
  user_count: number
  avg_scroll_y: number | null
  max_scroll_y: number | null
  event_count: number
  w_click_count: number
  t_click_count: number
}
/* eslint-enable */

interface LineChartOption {
  value: keyof LineChartData
  text: string
}

@Component
export default class StatLineChart extends Vue {
  @Prop({ type: Array, required: true })
  data!: IStatDataTable[]

  formattedData: LineChartData[] | null = null

  yItem: keyof LineChartData = 'count'

  options: LineChartOption[] = [
    { value: 'count', text: 'PV' },
    { value: 'session_count', text: 'Session' },
    { value: 'user_count', text: 'User' },
    { value: 'event_count', text: 'Event' },
    { value: 'w_click_count', text: 'Widget Click' },
    { value: 't_click_count', text: 'Trivial Click' },
    { value: 'avg_scroll_y', text: 'Scroll(AVG)' },
    { value: 'max_scroll_y', text: 'Scroll(MAX)' },
  ]

  @Watch('yItem')
  onYItemChanged() {
    this.formattedData = this.formatData
    this.renderGraph()
  }

  get formatData(): LineChartData[] {
    const result = []
    const grouped = groupBy(this.data, 'datetime')
    for (const datetime in grouped) {
      const d = grouped[datetime]
      const scrollCount = sumBy(d, 's_count')

      const data: LineChartData = {
        datetime: new Date(datetime),
        count: sumBy(d, 'count'),
        session_count: sumBy(d, 'session_count'),
        user_count: sumBy(d, 'user_count'),
        avg_scroll_y: null,
        max_scroll_y: null,
        event_count: sumBy(d, 'event_count'),
        w_click_count: sumBy(d, 'w_click_count'),
        t_click_count: sumBy(d, 't_click_count'),
      }

      if (scrollCount > 0) {
        data.avg_scroll_y =
          reduce(
            d,
            (r, o) => {
              if (!o.s_count) {
                return r
              }

              r += o.avg_scroll_y! * o.s_count
              return r
            },
            0
          ) / scrollCount
        // eslint-disable-next-line camelcase
        data.max_scroll_y = maxBy(d, 'max_scroll_y')?.max_scroll_y || null
      }
      result.push(data)
    }

    return sortBy(result, 'datetime')
  }

  renderGraph() {
    if (!this.formattedData) {
      this.formattedData = this.formatData
    }

    const data = this.formattedData
    const componentElement = d3select(this.$el)
    const cl = componentElement.select('.line-chart')
    const width = (cl.node() as Element).clientWidth
    const height = 200
    const margin = { top: 30, bottom: 60, right: 30, left: 60 }
    cl.selectAll('*').remove()
    const svg = cl.append('svg').attr('width', width).attr('height', height)

    const dates = data.map((d) => d.datetime)
    const xScale = scaleTime()
      .domain([d3min(dates) as Date, d3max(dates) as Date])
      .range([margin.left, width - margin.right])

    const yScale = scaleLinear()
      .domain([0, d3max(data.map((d) => d[this.yItem] as number)) as number])
      .range([height - margin.bottom, margin.top])
    const xAxis = axisBottom(xScale).tickFormat(
      timeFormat('%m/%d %H') as (
        dv: number | Date | { valueOf(): number },
        i: number
      ) => string
    )
    const yAxis = axisLeft(yScale).ticks(5)

    svg
      .append('g')
      .attr('transform', `translate(0, ${height - margin.bottom})`)
      .call(xAxis)
      .append('text')
      .attr('fill', 'black')
      .attr('x', (width - margin.left - margin.right) / 2 + margin.left)
      .attr('y', 35)
      .attr('text-anchor', 'middle')
      .attr('font-size', '10pt')
      .attr('font-weight', 'bold')
      .text('Time')

    svg
      .append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .call(yAxis)
      .append('text')
      .attr('fill', 'black')
      .attr('text-anchor', 'middle')
      .attr('x', -(height - margin.top - margin.bottom) / 2 - margin.top)
      .attr('y', -35)
      .attr('transform', 'rotate(-90)')
      .attr('font-weight', 'bold')
      .attr('font-size', '10pt')

    svg
      .append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', 'steelblue')
      .attr('stroke-width', 1.5)
      .attr(
        'd',
        d3line<LineChartData>()
          .x((d) => xScale(d.datetime))
          .y((d) => yScale(d[this.yItem] as number))
      )

    const focus = svg
      .append('g')
      .append('circle')
      .style('fill', 'none')
      .style('stroke', 'black')
      .style('r', 3)
      .style('opacity', 0)
    const focusText = cl
      .append('div')
      .attr('class', 'focus-text')
      .style('opacity', 0)
      .style('text-align', 'center')
      .style('position', 'absolute')
      .style('z-index', 255)

    const bisect = d3bisector((d: LineChartData) => {
      return d.datetime
    })

    svg
      .append('rect')
      .style('fill', 'none')
      .style('pointer-events', 'all')
      .attr('width', width)
      .attr('height', height)
      .on('mouseover', () => {
        focus.style('opacity', 1)
        focusText.style('opacity', 0.5)
      })
      .on('mouseout', () => {
        focus.style('opacity', 0)
        focusText.style('opacity', 0)
      })
      .on('mousemove', (event) => {
        let d = null
        if (data.length > 1) {
          const x0 = xScale.invert(d3pointer(event)[0])
          const i = bisect.center(data, x0, 1)
          if (i < data.length) {
            const d0 = data[i - 1]
            const d1 = data[i]
            d =
              x0.getTime() - d0.datetime.getTime() >
              d1.datetime.getTime() - x0.getTime()
                ? d1
                : d0
          } else {
            d = data[data.length - 1]
          }
        } else if (data.length === 1) {
          d = data[0]
        }
        if (d) {
          const formatTime = d3timeFormat('%Y-%m-%d')
          focus
            .attr('cx', xScale(d.datetime))
            .attr('cy', yScale(d[this.yItem] as number))
          focusText
            .html(formatTime(d.datetime) + ': ' + d[this.yItem])
            .style('top', yScale(d[this.yItem] as number) - 60 + 'px')

          const x = xScale(d.datetime)
          if (x > width - width / 6) {
            focusText.style('left', `${x - 150}px`)
          } else {
            focusText.style('left', `${x}px`)
          }
        }
      })
  }

  mounted() {
    this.renderGraph()
  }
}
</script>

<style lang="scss">
.stat-line-chart {
  .line-chart {
    position: relative;
    .focus-text {
      background-color: white;
      border: 1px solid #333333;
      padding: 8px;
      white-space: nowrap;
    }
  }
}
</style>
