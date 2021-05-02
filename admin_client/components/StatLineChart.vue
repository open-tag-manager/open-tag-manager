<template>
  <div>
    <div id="line-chart" />
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
import { select as d3select } from 'd3-selection'
import { scaleTime, scaleLinear } from 'd3-scale'
import { max as d3max, min as d3min } from 'd3-array'
import { axisBottom, axisLeft } from 'd3-axis'
import { timeFormat } from 'd3-time-format'
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
    const cl = d3select('#line-chart')
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
  }

  mounted() {
    this.renderGraph()
  }
}
</script>
