<template>
  <div class="stat-line-chart">
    <div class="guide d-flex">
      <div class="mr-4">Date: {{ selectedDate }}</div>
      <div class="data mr-4">
        <span class="mark">●</span>
        <span class="label mr-1">{{ selectedLabel }}:</span>
        <span class="number">{{ dataNum }}</span>
      </div>
      <div class="data-ma-14 mr-4">
        <span class="mark">●</span>
        <span class="label mr-1">MA(14):</span>
        <span class="number">{{ dataNumMa14 }}</span>
      </div>
      <div class="data-ma-30">
        <span class="mark">●</span>
        <span class="label mr-1">MA(30):</span>
        <span class="number">{{ dataNumMa30 }}</span>
      </div>
    </div>
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
import { pointer as d3pointer, select as d3select } from 'd3-selection'
import { scaleTime, scaleLinear } from 'd3-scale'
import { bisector as d3bisector, max as d3max, min as d3min } from 'd3-array'
import { axisBottom, axisLeft } from 'd3-axis'
import { timeFormat } from 'd3-time-format'
import { format as numberFormat } from 'd3-format'
import { line as d3line } from 'd3-shape'
import { IStatPageviewTimeSeriesTable } from '~/utils/api/stat'

type LineChartItem = 'pageview_count' | 'session_count' | 'user_count'

interface LineChartOption {
  value: LineChartItem
  text: string
}

interface LineChartData extends IStatPageviewTimeSeriesTable {
  datetime: Date
  [key: string]: any
}

@Component
export default class StatLineChart extends Vue {
  @Prop({ type: Array, required: true })
  data!: IStatPageviewTimeSeriesTable[]

  yItem: LineChartItem = 'pageview_count'

  options: LineChartOption[] = [
    { value: 'pageview_count', text: 'PV' },
    { value: 'session_count', text: 'Session' },
    { value: 'user_count', text: 'User' },
  ]

  selected: LineChartData | null = null

  @Watch('yItem')
  onYItemChanged() {
    this.renderGraph()
  }

  get selectedDate() {
    if (this.selected) {
      return timeFormat('%Y-%m-%d')(this.selected.datetime)
    }

    return '-'
  }

  get selectedLabel() {
    return this.options.find((o) => o.value === this.yItem)?.text
  }

  get dataNum() {
    if (this.selected) {
      return numberFormat(',')(this.selected[this.yItem])
    }

    return '-'
  }

  get dataNumMa14() {
    if (this.selected) {
      return numberFormat(',.2r')(this.selected[`${this.yItem}_14days`] / 14)
    }

    return '-'
  }

  get dataNumMa30() {
    if (this.selected) {
      return numberFormat(',.2r')(this.selected[`${this.yItem}_30days`] / 30)
    }

    return '-'
  }

  renderGraph() {
    const data: LineChartData[] = this.data.map((d) => {
      return { ...d, datetime: new Date(d.date) }
    })
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
      .attr('class', 'data')
      .attr('stroke-width', 1.5)
      .attr(
        'd',
        d3line<LineChartData>()
          .x((d) => xScale(d.datetime))
          .y((d) => yScale(d[this.yItem]))
      )

    svg
      .append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('class', 'data-ma-30')
      .attr('stroke-width', 1.5)
      .attr(
        'd',
        d3line<LineChartData>()
          .x((d) => xScale(d.datetime))
          .y((d) => {
            return yScale((d[`${this.yItem}_30days`] as number) / 30)
          })
      )

    svg
      .append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('class', 'data-ma-14')
      .attr('stroke-width', 1.5)
      .attr(
        'd',
        d3line<LineChartData>()
          .x((d) => xScale(d.datetime))
          .y((d) => {
            return yScale((d[`${this.yItem}_14days`] as number) / 14)
          })
      )

    const focus = svg
      .append('g')
      .append('circle')
      .style('fill', 'none')
      .style('stroke', 'black')
      .style('r', 3)
      .style('opacity', 0)

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
      })
      .on('mouseout', () => {
        focus.style('opacity', 0)
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
          focus
            .attr('cx', xScale(d.datetime))
            .attr('cy', yScale(d[this.yItem] as number))
          this.selected = d
        }
      })
  }

  mounted() {
    this.renderGraph()
  }
}
</script>

<style lang="scss" scoped>
$data-color: red;
$data-ma-14-color: pink;
$data-ma-30-color: steelblue;

.stat-line-chart {
  ::v-deep .line-chart {
    position: relative;

    .data {
      stroke: $data-color;
    }

    .data-ma-14 {
      stroke: $data-ma-14-color;
    }

    .data-ma-30 {
      stroke: $data-ma-30-color;
    }
  }

  .guide {
    padding: 0.5rem 0 0.5rem 80px;

    .number {
      display: inline-block;
      text-align: right;
      min-width: 30px;
    }

    .data {
      .mark {
        color: $data-color;
      }
    }

    .data-ma-14 {
      .mark {
        color: $data-ma-14-color;
      }
    }

    .data-ma-30 {
      .mark {
        color: $data-ma-30-color;
      }
    }
  }
}
</style>
