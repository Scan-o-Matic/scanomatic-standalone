import { getExtentFromMultipleArrs, getBaseLog } from './qc_normHelper';

const d3 = require('d3/d3.js');

if (!d3.scanomatic) {
  d3.scanomatic = {};
}

export default function DrawCurves(container, data, gt, gtWhen, yld) {
  // GrowthChart
  const chartMarginAll = 30;
  const chartMargin = {
    top: chartMarginAll, right: chartMarginAll, bottom: chartMarginAll, left: chartMarginAll,
  };
  const chartwidth = 350;
  const chartheight = 294;

  const chart = d3.select(container)
    .append('svg')
    .attr({
      width: chartwidth,
      height: chartheight,
      class: 'growthChart',
      margin: 3,
    });

  const defs = chart.append('defs');

  defs.append('marker')
    .attr({
      id: 'arrow',
      viewBox: '0 -5 10 10',
      refX: 5,
      refY: 0,
      markerWidth: 4,
      markerHeight: 4,
      orient: 'auto',
    })
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('class', 'arrowHead');

  defs.append('marker')
    .attr({
      id: 'arrow2',
      viewBox: '0 -5 10 10',
      refX: 5,
      refY: 0,
      markerWidth: 4,
      markerHeight: 4,
      orient: 'auto-start-reverse',
    })
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('class', 'arrowHead');

  // chart
  const gChart = d3.scanomatic.growthChart();
  gChart.data(data);
  gChart.width(chartwidth);
  gChart.height(chartheight);
  gChart.margin(chartMargin);
  gChart.generationTimeWhen(gtWhen);
  gChart.generationTime(gt);
  gChart.growthYield(yld);
  gChart(chart);
}

d3.scanomatic.growthChart = () => {
  // properties
  let data;
  let margin;
  let height;
  let width;
  let generationTimeWhen;
  let generationTime;
  let growthYield;

  // local variables
  let g;

  function addAxis(xScale, yScale, chartHeight) {
    const xAxis = d3.svg.axis()
      .scale(xScale)
      .orient('bottom');

    const yAxis = d3.svg.axis()
      .scale(yScale)
      .orient('left')
      .tickFormat(d3.format('.0e'));

    g.append('g')
      .attr('class', 'x axis')
      .attr('transform', `translate(0,${chartHeight})`)
      .call(xAxis);

    g.append('g')
      .attr('class', 'y axis')
      .call(yAxis)
      .append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', 6)
      .attr('dy', '.5em')
      .style('text-anchor', 'end')
      .style('font-size', '11')
      .text('Population size [cells]');
  }

  function addSeries(rawData, smoothData, xScale, yScale) {
    const lineFun = d3.svg.line()
      .x(d => xScale(d.time))
      .y(d => yScale(d.value))
      .interpolate('linear');

    g.append('g')
      .classed('series', true)
      .append('path')
      .attr({
        class: 'raw',
        d: lineFun(rawData),
      });

    g.append('g')
      .classed('series', true)
      .append('path')
      .attr({
        class: 'smooth',
        d: lineFun(smoothData),
      });
  }

  function getYOffset(y, offset) {
    return (y > 100) ? y - offset : y + offset;
  }

  function addMetaGt(smoothData, xScale, yScale) {
    if (generationTime == null || generationTimeWhen == null) return;

    const lineStartOffset = 50;
    const lineEndOffset = 10;

    const smoothGtTime = generationTimeWhen;
    let smoothGtValue = 0;
    for (let i = 0; i < smoothData.length; i += 1) {
      const approx = d3.round(smoothData[i].time, 2);
      if (approx === d3.round(smoothGtTime, 2)) { smoothGtValue = smoothData[i].value; }
    }

    const gtX = xScale(smoothGtTime);
    const gtY = yScale(smoothGtValue);

    const gMetaGt = g.append('g')
      .classed('meta gt', true);

    gMetaGt.append('circle')
      .attr({
        cx: gtX,
        cy: gtY,
        r: 4,
        fill: 'red',
      });

    gMetaGt.append('line')
      .attr({
        class: 'arrow',
        'marker-end': 'url(#arrow)',
        x1: gtX,
        y1: getYOffset(gtY, lineStartOffset),
        x2: gtX,
        y2: getYOffset(gtY, lineEndOffset),
        stroke: 'black',
        'stroke-width': 1.5,
      });

    gMetaGt.append('text')
      .attr({
        x: gtX - 10,
        y: getYOffset(gtY, 55),
      })
      .text('GT');
    // Py=m (Px-x) + Py
    console.log(`GT:${generationTime}`);
    console.log(`GTTimeWhen:${generationTimeWhen}`);
    console.log(`GTTimeWhenValue:${smoothGtValue}`);
    const windowSize = 4;
    const gtSlope = 1 / generationTime;
    const l = parseFloat(smoothGtTime) - windowSize;
    const leftXLimit = xScale(l);
    const logPy = getBaseLog(2, smoothGtValue);
    const yLeftLogged = logPy - (windowSize * gtSlope);
    const yLeft = 2 ** yLeftLogged;
    const leftYLimit = yScale(yLeft);

    gMetaGt.append('line')
      .attr({
        x1: gtX,
        y1: gtY,
        x2: leftXLimit,
        y2: leftYLimit,
        stroke: 'blue',
        'stroke-width': 3,
      });

    const r = parseFloat(smoothGtTime) + windowSize;
    const rightXlimit = xScale(r);
    const yRightLogged = (windowSize * gtSlope) + logPy;
    const yRight = 2 ** yRightLogged;
    const rightYLimit = yScale(yRight);

    gMetaGt.append('line')
      .attr({
        x1: gtX,
        y1: gtY,
        x2: rightXlimit,
        y2: rightYLimit,
        stroke: 'blue',
        'stroke-width': 3,
      });
  }

  function addMetaYield(smoothData, xScale, yScale) {
    if (growthYield == null) return;

    const smoothYieldValue = growthYield;
    let smoothYieldTime = 0;
    for (let i = 0; i < smoothData.length; i += 1) {
      if (smoothData[i].value >= smoothYieldValue) {
        smoothYieldTime = smoothData[i].time;
        break;
      }
    }

    const gtX = xScale(smoothYieldTime);
    const gtY = yScale(smoothYieldValue);
    const baseX = gtX;
    const baseY = yScale(smoothData[0].value);
    console.log(`Yield time:${smoothYieldTime}`);
    console.log(`Yield value:${smoothYieldValue}`);

    const gMetaYeild = g.append('g')
      .classed('meta yield', true);

    gMetaYeild.append('line')
      .attr({
        class: 'arrow',
        'marker-end': 'url(#arrow)',
        'marker-start': 'url(#arrow2)',
        x1: gtX,
        y1: gtY + 5,
        x2: baseX,
        y2: baseY - 5,
        stroke: 'black',
        'stroke-width': 1.5,
      });

    const middle = (baseY - gtY) / 2;
    gMetaYeild.append('text')
      .attr({
        x: gtX + 3,
        y: gtY + middle,
      })
      .text('Yield');
  }

  function update() {
    function getDataObject(time, value) {
      const dataObject = [];
      let i = 0;
      time.forEach((timePoint) => {
        const p = { time: timePoint, value: value[i] };
        dataObject.push(p);
        i += 1;
      });
      return dataObject;
    }

    // data
    const serRaw = data.raw_data;
    const serSmooth = data.smooth_data;
    const time = data.time_data;
    // chart
    const w = width - margin.left - margin.right;
    const h = height - margin.top - margin.bottom;

    if (serRaw.length !== time.length || serSmooth.length !== time.length) {
      throw Error('GrowthData lengths do not match!!!');
    }

    const odExtend = getExtentFromMultipleArrs(serRaw, serSmooth);

    const rawData = getDataObject(time, serRaw);
    const smoothData = getDataObject(time, serSmooth);

    const xScale = d3.scale.linear()
      .domain(d3.extent(time))
      .range([0, w]);

    const yScale = d3.scale.log()
      .base(2)
      .domain(d3.extent(odExtend))
      .range([h, 0]);

    addAxis(xScale, yScale, h);

    addSeries(rawData, smoothData, xScale, yScale);

    addMetaGt(smoothData, xScale, yScale);

    addMetaYield(smoothData, xScale, yScale);
  }

  function chart(container) {
    g = container.append('g')
      .attr({
        transform: `translate(${margin.left},${margin.top})`,
        class: 'PlotArea',
      });
    update();
  }

  chart.update = update;

  chart.data = (value) => {
    if (!arguments.length) return data;
    data = value;
    return chart;
  };

  chart.margin = (value) => {
    if (!arguments.length) return margin;
    margin = value;
    return chart;
  };

  chart.width = (value) => {
    if (!arguments.length) return width;
    width = value;
    return chart;
  };

  chart.height = (value) => {
    if (!arguments.length) return height;
    height = value;
    return chart;
  };

  chart.generationTimeWhen = (value) => {
    if (!arguments.length) return generationTimeWhen;
    generationTimeWhen = value;
    return chart;
  };

  chart.generationTime = (value) => {
    if (!arguments.length) return generationTime;
    generationTime = value;
    return chart;
  };

  chart.growthYield = (value) => {
    if (!arguments.length) return growthYield;
    growthYield = value;
    return chart;
  };

  return chart;
};
