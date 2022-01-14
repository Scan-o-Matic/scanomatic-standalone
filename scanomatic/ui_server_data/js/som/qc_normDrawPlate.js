import * as d3 from 'd3';

const classExperimentSelected = 'ExperimentSelected';
const dispatcherSelectedExperiment = 'SelectedExperiment';
let markingSelection = false;
const allowMarking = false;
export const plateMetaDataType = {
  OK: 'OK',
  BadData: 'BadData',
  Empty: 'Empty',
  NoGrowth: 'NoGrowth',
  UndecidedProblem: 'UndecidedProblem',
};

if (!d3.scanomatic) {
  d3.scanomatic = {};
}

export function addSymbolToSVG(svgRoot, type) {
  let badDataSym;
  let okSym;
  switch (type) {
  case plateMetaDataType.BadData:
    badDataSym = svgRoot.append('symbol')
      .attr({
        id: 'symBadData',
        viewBox: '0 0 100 125',
      });
    badDataSym.append('path')
      .attr('d', 'M94.202,80.799L55.171,13.226c-1.067-1.843-3.022-2.968-5.147-2.968c-0.008,0-0.016,0-0.023,0s-0.016,0-0.023,0  c-2.124,0-4.079,1.125-5.147,2.968L5.798,80.799c-1.063,1.85-1.063,4.124,0,5.969c1.057,1.846,3.024,2.976,5.171,2.976h78.063  c2.146,0,4.114-1.13,5.171-2.976C95.266,84.923,95.266,82.646,94.202,80.799z M14.412,81.79L50,20.182L85.588,81.79H14.412z');
    badDataSym.append('polygon')
      .attr('points', '64.512,70.413 56.414,62.164 64.305,54.188 57.873,47.826 50.075,55.709 42.212,47.7 35.757,54.038 43.713,62.141 35.489,70.455 41.92,76.817 50.051,68.598 58.057,76.751');

    svgRoot.append('symbol')
      .attr({
        id: 'symNoGrowth',
        viewBox: '0 0 100 125',
      })
      .append('path')
      .attr('d', 'M50,95c24.853,0,45-20.147,45-45C95,25.147,74.853,5,50,5S5,25.147,5,50C5,74.853,25.147,95,50,95z M25,45h50v10H25V45z');
    // CREDIT: Created by Arthur Shlain from from the Noun Project
    break;
  case plateMetaDataType.Empty:
    svgRoot.append('symbol')
      .attr({
        id: 'symEmpty',
        viewBox: '0 0 24 30',
      })
      .append('path')
      .attr('d', 'M22.707,1.293c-0.391-0.391-1.023-0.391-1.414,0L16.9,5.686C15.546,4.633,13.849,4,12,4c-4.418,0-8,3.582-8,8  c0,1.849,0.633,3.546,1.686,4.9l-4.393,4.393c-0.391,0.391-0.391,1.023,0,1.414C1.488,22.902,1.744,23,2,23s0.512-0.098,0.707-0.293  L7.1,18.314C8.455,19.367,10.151,20,12,20c4.418,0,8-3.582,8-8c0-1.849-0.633-3.545-1.686-4.9l4.393-4.393  C23.098,2.316,23.098,1.684,22.707,1.293z M6,12c0-3.309,2.691-6,6-6c1.294,0,2.49,0.416,3.471,1.115l-8.356,8.356  C6.416,14.49,6,13.294,6,12z M18,12c0,3.309-2.691,6-6,6c-1.294,0-2.49-0.416-3.471-1.115l8.356-8.356C17.584,9.51,18,10.706,18,12z');
    // CREDIT: Created by ? from from the Noun Project
    break;
  case plateMetaDataType.OK:
    okSym = svgRoot.append('symbol')
      .attr({
        id: 'symOK',
        viewBox: '0 0 90 112.5',
      });
    okSym.append('path')
      .attr('d', 'M38.3,61.3L38.3,61.3c-0.9,0-1.7-0.3-2.3-1L25.9,50.2c-1.3-1.3-1.3-3.4,0-4.7c1.3-1.3,3.4-1.3,4.7,0l7.8,7.8l22.6-22.6   c1.3-1.3,3.4-1.3,4.7,0c1.3,1.3,1.3,3.4,0,4.7L40.7,60.3C40.1,60.9,39.2,61.3,38.3,61.3z');
    okSym.append('path')
      .attr('d', 'M45.7,81.3C26,81.3,9.9,65.3,9.9,45.5C9.9,25.8,26,9.7,45.7,9.7s35.8,16.1,35.8,35.8C81.6,65.3,65.5,81.3,45.7,81.3z    M45.7,16.3c-16.1,0-29.2,13.1-29.2,29.2s13.1,29.2,29.2,29.2S75,61.6,75,45.5S61.9,16.3,45.7,16.3z');
    // CREDIT: Created by Louis Buck from from the Noun Project
    break;
  case plateMetaDataType.NoGrowth:
    break;
  case plateMetaDataType.UndecidedProblem:
    svgRoot.append('symbol')
      .attr({
        id: 'symUndecided2',
        viewBox: '0 0 100 125',
      })
      .append('path')
      .attr('d', 'M43.475,69.043c0,1.633,0.518,2.965,1.551,4.02c1.057,1.033,2.369,1.572,3.941,1.572   c1.594,0,2.926-0.539,3.979-1.572c1.074-1.055,1.613-2.387,1.613-4.02c0-1.613-0.539-2.965-1.613-3.998   c-1.053-1.057-2.385-1.574-3.979-1.574c-1.572,0-2.885,0.518-3.941,1.574C43.992,66.078,43.475,67.43,43.475,69.043z    M45.363,57.959h7.504c-0.201-1.531-0.1-2.289,0.359-3.521c0.475-1.234,1.092-2.408,1.869-3.5c0.756-1.098,1.631-2.15,2.607-3.166   c0.953-0.996,1.869-2.051,2.705-3.143c0.836-1.096,1.551-2.25,2.109-3.463c0.576-1.236,0.855-2.588,0.855-4.119   c0-1.971-0.338-3.68-0.994-5.154c-0.678-1.492-1.633-2.727-2.865-3.721c-1.236-1.016-2.709-1.77-4.379-2.268   c-1.691-0.498-3.521-0.758-5.512-0.758c-2.727,0-5.172,0.598-7.342,1.771c-2.189,1.154-4.08,2.646-5.652,4.479l4.756,4.217   c1.074-1.154,2.25-2.049,3.48-2.725c1.256-0.658,2.629-0.996,4.16-0.996c1.893,0,3.365,0.518,4.438,1.57   c1.055,1.057,1.594,2.43,1.594,4.16c0,1.096-0.279,2.109-0.816,3.064c-0.559,0.957-1.236,1.93-2.051,2.906   c-0.816,0.973-1.691,1.99-2.605,3.004c-0.918,1.035-1.732,2.127-2.449,3.322c-0.715,1.195-1.254,2.51-1.631,3.939   C45.127,55.293,45.107,56.25,45.363,57.959z M11,50c0,21.531,17.471,39,39,39c21.531,0,39-17.469,39-39S71.531,11,50,11   C28.471,11,11,28.469,11,50z M18.184,50c0-17.57,14.246-31.818,31.816-31.818S81.818,32.43,81.818,50S67.57,81.818,50,81.818   S18.184,67.57,18.184,50z');
    // CREDIT: Created by Ervin Bolat from from the Noun Project
    break;
  default:
  }
  return null;
}

function addSymbolsToSVG(svgRoot) {
  addSymbolToSVG(svgRoot, plateMetaDataType.BadData);
  addSymbolToSVG(svgRoot, plateMetaDataType.Empty);
  addSymbolToSVG(svgRoot, plateMetaDataType.NoGrowth);
  addSymbolToSVG(svgRoot, plateMetaDataType.OK);
  addSymbolToSVG(svgRoot, plateMetaDataType.UndecidedProblem);
}

function addSelectionHandling(svgRoot) {
  svgRoot.on(
    'mousedown',
    () => {
      if (!allowMarking) return;

      if (!d3.event.ctrlKey) {
        d3.selectAll('g.expNode.selected').classed('selected', false);
      }

      const p = d3.mouse(this);

      svgRoot.append('rect')
        .attr({
          rx: 6,
          ry: 6,
          class: 'selection',
          x: p[0],
          y: p[1],
          width: 0,
          height: 0,
        });
    },
  )
    .on(
      'mousemove',
      () => {
        if (!allowMarking) return;
        const s = svgRoot.select('rect.selection');
        if (!s.empty()) {
          markingSelection = true;
          const p = d3.mouse(this);
          const d = {
            x: parseInt(s.attr('x'), 10),
            y: parseInt(s.attr('y'), 10),
            width: parseInt(s.attr('width'), 10),
            height: parseInt(s.attr('height'), 10),
          };
          const move = {
            x: p[0] - d.x,
            y: p[1] - d.y,
          };
          if (move.x < 1 || (move.x * 2 < d.width)) {
            [d.x] = p;
            d.width -= move.x;
          } else { d.width = move.x; }
          if (move.y < 1 || (move.y * 2 < d.height)) {
            [, d.y] = p;
            d.height -= move.y;
          } else { d.height = move.y; }
          s.attr(d);

          d3.selectAll('g.expNode.selection.selected').classed('selected', false);

          d3.selectAll('.plateWell')
            .each((stateData) => {
              if (
                !d3.select(this).classed('selected')
                  && stateData.celStartX >= d.x
                  && stateData.celEndX <= d.x + d.width
                  && stateData.celStartY >= d.y
                  && stateData.celEndY <= d.y + d.height
              ) {
                d3.select(this.parentNode)
                  .classed('selection', true)
                  .classed('selected', true);
              }
            });
        }
      },
    )
    .on(
      'mouseup',
      () => {
        if (!allowMarking) return;
        markingSelection = false;
        svgRoot.selectAll('rect.selection').remove();
        d3.selectAll('g.expNode.selection').classed('selection', false);
      },
    )
    .on(
      'mouseout',
      () => {
        if (d3.event.relatedTarget != null && d3.event.relatedTarget.tagName === 'HTML') {
          svgRoot.selectAll('rect.selection').remove();
          d3.selectAll('g.expNode.selection').classed('selection', false);
        }
      },
    );
}

export function DrawPlate(container, data, growthMetaData, plateMetaData, phenotypeName, dispatch) {
  // plate
  const cols = data[0].length;
  const rows = data.length;
  // experiment
  const circleRadius = 4;
  const circleMargin = 1;
  const cellSize = (circleRadius * 2) + circleMargin;
  // heatmap
  const heatmapMargin = 7;
  const scaleWidth = 30;
  const gridwidth = (cols * cellSize) + scaleWidth + (heatmapMargin * 2);
  const gridheight = (rows * cellSize) + (heatmapMargin * 2);
  const colorScheme = ['blue', 'white', 'red'];
  // heatmap legend
  const legendWidth = 25;
  const legendMargin = 5;

  // SetDebugText(data, cols, rows);

  const grid = d3.select(container)
    .append('svg')
    .attr({
      width: gridwidth + legendMargin + legendWidth,
      height: gridheight,
      class: 'PlateHeatMap',
    });


  addSelectionHandling(grid);
  addSymbolsToSVG(grid);

  const plateGroup = grid.append('g').classed('gHeatmap', true);

  // heatmap
  const heatMap = d3.scanomatic.plateHeatmap();
  heatMap.data(data);
  heatMap.phenotypeName(phenotypeName);
  heatMap.growthMetaData(growthMetaData);
  heatMap.plateMetaData(plateMetaData);
  heatMap.cellSize(cellSize);
  heatMap.cellRadius(circleRadius);
  heatMap.setColorScale(colorScheme);
  heatMap.margin(heatmapMargin);
  heatMap.legendWidth(legendWidth);
  heatMap.legendMargin(legendMargin);
  heatMap.displayLegend(true);
  heatMap.dispatch2(dispatch);
  heatMap(plateGroup);
  // heatMap.on(dispatcherSelectedExperiment, function (datah) {
  //    console.log("dispatched:" + datah);
  // });
  return d3.rebind(DrawPlate, heatMap, 'on');
}

export function getValidSymbol(type) {
  switch (type) {
  case plateMetaDataType.BadData:
    return 'symBadData';
  case plateMetaDataType.Empty:
    return 'symEmpty';
  case plateMetaDataType.OK:
    return 'symOK';
  case plateMetaDataType.NoGrowth:
    return 'symNoGrowth';
  case plateMetaDataType.UndecidedProblem:
    return 'symUndecided2';

  default:
    return null;
  }
}

function SetDebugText(data, cols, rows) { // eslint-disable-line no-unused-vars
  d3.select('#text').append('p').text(`cols = ${cols}`);
  d3.select('#text').append('p').text(`rows = ${rows}`);

  const min = d3.min(data[0]);
  const max = d3.max(data[0]);
  const mean = d3.mean(data[0]);
  d3.select('#text').append('p').text(`min = ${min}`);
  d3.select('#text').append('p').text(`max = ${max}`);
  d3.select('#text').append('p').text(`mean = ${mean}`);
}

d3.scanomatic.plateHeatmap = () => {
  // properties
  let data;
  let growthMetaData;
  let plateMetaData;
  let cellSize;
  let cellRadius;
  let colorScale;
  let colorSchema;
  let margin;
  let displayLegend;
  let legendMargin;
  let legendWidth;
  let phenotypeName;
  let dispatch2;

  // local variables
  let g;
  let cols;
  let rows;
  let phenotypeMin;
  let phenotypeMax;
  let phenotypeMean;
  let heatMapCelWidth;
  let heatMapCelHeight;
  const dispatch = d3.dispatch(dispatcherSelectedExperiment);
  const numberFormat = '0.3n';

  function getValidColor(phenotype, dataType) {
    let color;
    if (dataType === plateMetaDataType.OK) { color = colorScale(phenotype); } else { color = 'white'; }
    return color;
  }

  function createLegend(container) {
    const startX = margin + (cols * cellSize) + legendMargin;
    const startY = margin;
    const heatMaphight = (rows * cellSize);
    const gLegendScale = container.append('g');

    const gradient = gLegendScale
      .append('linearGradient')
      .attr({
        y1: '0%',
        y2: '100%',
        x1: '0',
        x2: '0',
        id: 'gradient',
      });

    gradient
      .append('stop')
      .attr({
        offset: '0%',
        'stop-color': colorSchema[2],
      });

    gradient
      .append('stop')
      .attr({
        offset: '50%',
        'stop-color': colorSchema[1],
      });

    gradient
      .append('stop')
      .attr({
        offset: '100%',
        'stop-color': colorSchema[0],
      });

    gLegendScale.append('rect')
      .attr({
        y: startY,
        x: startX,
        width: legendWidth,
        height: heatMaphight,
      }).style({
        fill: 'url(#gradient)',
        'stroke-width': 2,
        stroke: 'black',
      });

    const gLegendaxis = container.append('g').classed('HeatMapLegendAxis', true);

    const dom = [phenotypeMax, phenotypeMin];
    // d3.extent(data[0]).reverse()
    const legendScale = d3.scale.linear()
      .domain(dom)
      .rangeRound([startY, heatMaphight])
      .nice();

    const gradAxis = d3.svg.axis()
      .scale(legendScale)
      .orient('right')
      .tickSize(10)
      .ticks(10)
      .tickFormat(d3.format(numberFormat));

    gradAxis(gLegendaxis);
    gLegendaxis.attr({
      transform: `translate(${(startX + legendWidth) - 9}, ${margin / 2})`,
    });
    gLegendaxis.selectAll('path').style({ fill: 'none', stroke: '#000' });
    gLegendaxis.selectAll('line').style({ stroke: '#000' });
  }

  function update() {
    function getRowFromId(id) {
      const tmp = id.replace('id', '');
      const row = tmp.substr(0, tmp.indexOf('_'));
      return row;
    }

    let toolTipDiv = d3.select('#toolTipDiv');
    if (toolTipDiv.empty()) {
      toolTipDiv = d3.select('body').append('div')
        .attr('class', 'tooltip')
        .attr('id', 'toolTipDiv')
        .style('opacity', 0);
    }

    function setExperiment(id) {
      const well = d3.select(`#${id}`);
      if (well.empty()) { return; }

      const row = getRowFromId(id);
      const col = well.attr('data-col');
      const metaDataGt = well.attr('data-meta-gt');
      const metaDataGtWhen = well.attr('data-meta-gtWhen');
      const metaDataYield = well.attr('data-meta-yield');
      const coord = `${row},${col}`;
      const coordinate = `[${coord}]`;
      let phenotype = 0;
      const fmt = d3.format(numberFormat);
      well.attr(
        '',
        (d) => { phenotype = fmt(d.phenotype); },
      );
      const exp = {
        id, coord, metaDataGt, metaDataGtWhen, metaDataYield, phenotype: phenotypeName,
      };
      // deselect preavius selections
      const sel = g.selectAll(`.${classExperimentSelected}`);
      sel.classed(classExperimentSelected, false);
      sel.attr({ 'stroke-width': 0 });
      // new selection
      const newSel = well;
      newSel.classed(classExperimentSelected, true);
      newSel.attr({
        stroke: 'black',
        'stroke-width': 3,
      });
      // trigger click and send coordinate
      toolTipDiv.transition().duration(0).style('opacity', 0);
      d3.select('#sel').selectAll('*').remove();
      d3.select('#sel').text(`Experiment ${coordinate}, Value ${phenotype}`);
      dispatch[dispatcherSelectedExperiment](exp);
    }

    function setShapes(node) {
      // ok metadata
      node
        .filter(d => d.metaType === plateMetaDataType.OK)
        .append('circle')
        .attr({
          class: 'plateWell OK',
          fill(d) { return getValidColor(d.phenotype, d.metaType); },
          id(d) { return `id${d.row}_${d.col}`; },
          'fill-opacity': '1',
          r: cellRadius,
          cy(d) { return d.celStartY + cellRadius; },
          cx(d) { return d.celStartX + cellRadius; },
          'data-col': d => d.col,
          'data-meta-gt': d => d.metaGT,
          'data-meta-gtWhen': d => d.metaGtWhen,
          'data-meta-yield': d => d.metaYield,
          'data-meta-type': d => d.metaType,
        });

      // bad metadata
      node
        .filter(d => d.metaType !== plateMetaDataType.OK)
        .append('rect')
        .attr({
          class: 'plateWell Marked',
          fill(d) { return getValidColor(d.phenotype, d.metaType); },
          id(d) { return `id${d.row}_${d.col}`; },
          'fill-opacity': '1',
          y(d) { return d.celStartY; },
          x(d) { return d.celStartX; },
          width: heatMapCelWidth,
          height: heatMapCelHeight,
          'data-col': d => d.col,
          'data-meta-gt': d => d.metaGT,
          'data-meta-gtWhen': d => d.metaGtWhen,
          'data-meta-yield': d => d.metaYield,
          'data-meta-type': d => d.metaType,
        });
    }

    function setSymbols(node) {
      // Empty
      node
        .filter(d => d.metaType === plateMetaDataType.Empty)
        .append('use')
        .attr({
          class: 'plateWellSymbol',
          'xlink:href': d => `#${getValidSymbol(d.metaType)}`,
          x(d) { return d.celStartX - 2; },
          y(d) { return d.celStartY - 0.8; },
          width: cellRadius * 3,
          height: cellRadius * 3,
        });

      // UndecidedProblem
      node
        .filter(d => d.metaType === plateMetaDataType.UndecidedProblem)
        .append('use')
        .attr({
          class: 'plateWellSymbol',
          'xlink:href': d => `#${getValidSymbol(d.metaType)}`,
          x(d) { return d.celStartX - 2; },
          y(d) { return d.celStartY; },
          width: cellRadius * 3,
          height: cellRadius * 2,
        });

      // BadData
      node
        .filter(d => d.metaType === plateMetaDataType.BadData)
        .append('use')
        .attr({
          class: 'plateWellSymbol',
          'xlink:href': d => `#${getValidSymbol(d.metaType)}`,
          x(d) { return d.celStartX - 2; },
          y(d) { return d.celStartY; },
          width: cellRadius * 3,
          height: cellRadius * 2,
        });

      // NoGrowth
      node
        .filter(d => d.metaType === plateMetaDataType.NoGrowth)
        .append('use')
        .attr({
          class: 'plateWellSymbol',
          'xlink:href': d => `#${getValidSymbol(d.metaType)}`,
          x(d) { return d.celStartX - 1; },
          y(d) { return d.celStartY; },
          width: cellRadius * 2.5,
          height: cellRadius * 2.5,
        });
    }

    function reDrawExperiment(id, mark) {
      const node = d3.select(`#${id}`);
      const parent = d3.select(node.node().parentNode);
      const newData = parent.data();
      newData[0].metaType = mark;
      parent.data(newData);
      parent.selectAll('*').remove();
      setShapes(parent);
      setSymbols(parent);
    }

    function onClick(rowNode, thisNode) {
      const row = rowNode.attr('data-row');
      const well = thisNode.select('.plateWell');
      const col = well.attr('data-col');
      const id = well.attr('id');
      const metaDataGt = well.attr('data-meta-gt');
      const metaDataGtWhen = well.attr('data-meta-gtWhen');
      const metaDataYield = well.attr('data-meta-yield');
      const coord = `${row},${col}`;
      const coordinate = `[${coord}]`;
      let phenotype = 0;
      const fmt = d3.format(numberFormat);
      well.attr(
        '',
        (d) => { phenotype = fmt(d.phenotype); },
      );
      const exp = {
        id, coord, metaDataGt, metaDataGtWhen, metaDataYield, phenotype: phenotypeName,
      };
      // deselect preavius selections
      const sel = g.selectAll(`.${classExperimentSelected}`);
      sel.classed(classExperimentSelected, false);
      sel.attr({ 'stroke-width': 0 });
      // new selection
      const newSel = well;
      newSel.classed(classExperimentSelected, true);
      newSel.attr({
        stroke: 'black',
        'stroke-width': 3,
      });
      // trigger click and send coordinate
      toolTipDiv.transition().duration(0).style('opacity', 0);
      d3.select('#sel').selectAll('*').remove();
      d3.select('#sel').text(`Experiment ${coordinate}, Value ${phenotype}`);
      dispatch[dispatcherSelectedExperiment](exp);
    }

    function onMouseOut(node) {
      node.select('.plateWell').attr('fill', d => getValidColor(d.phenotype, d.metaType));
      node.select('.plateWellSymbol').attr('fill', 'black');

      toolTipDiv.transition()
        .duration(0)
        .style('opacity', 0);
    }

    function onMouseOver(node) {
      if (markingSelection === true) return;

      const size = 50;

      const fmt = d3.format(numberFormat);
      toolTipDiv.transition()
        .duration(0)
        .style('opacity', 0.9);

      node.select('.plateWellSymbol')
        .attr('fill', 'white');

      toolTipDiv.html('');
      const toolTipIcon = toolTipDiv.append('svg')
        .attr({
          width: size,
          height: size,
          style: 'float: left',
        });

      addSymbolsToSVG(toolTipIcon);

      node.select('.plateWell')
        .attr('fill', 'black')
        .attr('', (d) => {
          toolTipIcon.append('use')
            .attr({
              class: 'toolTipSymbol',
              'xlink:href': () => `#${getValidSymbol(d.metaType)}`,
              x: 0,
              y: 5,
              width: size,
              height: size,
              fill: 'white',
            });

          toolTipDiv.append('div').text(phenotypeName);
          toolTipDiv.append('div').text(fmt(d.phenotype));
          toolTipDiv
            .style('left', `${d3.event.pageX}px`)
            .style('top', `${d3.event.pageY - size}px`);
        });
    }

    function addmetaDataType(metaDataType, typeName) {
      const dataType = [];
      let badDataElement;
      for (let k = 0; k < metaDataType[0].length; k += 1) {
        badDataElement = { row: metaDataType[0][k], col: metaDataType[1][k], type: typeName };
        dataType.push(badDataElement);
      }
      return dataType;
    }

    function findPlateMetaData(row, col, metaData) {
      for (let typeI = 0; typeI < metaData.length; typeI += 1) {
        const type = metaData[typeI];
        for (let itemI = 0; itemI < type.length; itemI += 1) {
          const item = type[itemI];
          if (item.row === row && item.col === col) { return item; }
        }
      }
      return { row, col, type: plateMetaDataType.OK };
    }

    function composeMetadata() {
      // compose from plate metadata
      const plateMetaDataComp = [];
      plateMetaDataComp.push(addmetaDataType(
        plateMetaData.plate_BadData,
        plateMetaDataType.BadData,
      ));
      plateMetaDataComp.push(addmetaDataType(
        plateMetaData.plate_Empty,
        plateMetaDataType.Empty,
      ));
      plateMetaDataComp.push(addmetaDataType(
        plateMetaData.plate_NoGrowth,
        plateMetaDataType.NoGrowth,
      ));
      plateMetaDataComp.push(addmetaDataType(
        plateMetaData.plate_UndecidedProblem,
        plateMetaDataType.UndecidedProblem,
      ));

      // compose from plate data and growth metadata
      const plate = [];
      for (let i = 0; i < rows; i += 1) {
        const row = [];
        for (let j = 0; j < cols; j += 1) {
          const metaData = findPlateMetaData(i, j, plateMetaDataComp);
          const x = margin + (j * cellSize);
          const y = margin + (i * cellSize);
          const metaGt = (
            growthMetaData.gt === undefined ? null : growthMetaData.gt[i][j]
          );
          const metaGtWhen = (
            growthMetaData.gtWhen === undefined ? null : growthMetaData.gtWhen[i][j]
          );
          const metaYield = (
            growthMetaData.yld === undefined ? null : growthMetaData.yld[i][j]
          );
          const col = {
            col: j,
            row: i,
            celStartX: x,
            celStartY: y,
            celEndX: x + heatMapCelWidth,
            celEndY: y + heatMapCelHeight,
            phenotype: data[i][j],
            metaGT: metaGt,
            metaGtWhen,
            metaYield,
            metaType: metaData.type,
          };
          row.push(col);
        }
        plate.push(row);
      }
      return plate;
    }

    function addSymbols(nodes) {
      // Empty
      nodes
        .filter(d => d.metaType === plateMetaDataType.Empty)
        .append('use')
        .attr({
          class: 'plateWellSymbol',
          'xlink:href': d => `#${getValidSymbol(d.metaType)}`,
          x(d) { return d.celStartX - 2; },
          y(d) { return d.celStartY - 0.8; },
          width: cellRadius * 3,
          height: cellRadius * 3,
        });

      // UndecidedProblem
      nodes
        .filter(d => d.metaType === plateMetaDataType.UndecidedProblem)
        .append('use')
        .attr({
          class: 'plateWellSymbol',
          'xlink:href': d => `#${getValidSymbol(d.metaType)}`,
          x(d) { return d.celStartX - 2; },
          y(d) { return d.celStartY; },
          width: cellRadius * 3,
          height: cellRadius * 2,
        });

      // BadData
      nodes
        .filter(d => d.metaType === plateMetaDataType.BadData)
        .append('use')
        .attr({
          class: 'plateWellSymbol',
          'xlink:href': d => `#${getValidSymbol(d.metaType)}`,
          x(d) { return d.celStartX - 2; },
          y(d) { return d.celStartY; },
          width: cellRadius * 3,
          height: cellRadius * 2,
        });

      // NoGrowth
      nodes
        .filter(d => d.metaType === plateMetaDataType.NoGrowth)
        .append('use')
        .attr({
          class: 'plateWellSymbol',
          'xlink:href': d => `#${getValidSymbol(d.metaType)}`,
          x(d) { return d.celStartX - 1; },
          y(d) { return d.celStartY; },
          width: cellRadius * 2.5,
          height: cellRadius * 2.5,
        });
    }

    function addShapes(nodes) {
      // ok metadata
      nodes
        .filter(d => d.metaType === plateMetaDataType.OK)
        .append('circle')
        .attr({
          class: 'plateWell OK',
          fill(d) { return getValidColor(d.phenotype, d.metaType); },
          id(d) { return `id${d.row}_${d.col}`; },
          'fill-opacity': '1',
          r: cellRadius,
          cy(d) { return d.celStartY + cellRadius; },
          cx(d) { return d.celStartX + cellRadius; },
          'data-col': d => d.col,
          'data-meta-gt': d => d.metaGT,
          'data-meta-gtWhen': d => d.metaGtWhen,
          'data-meta-yield': d => d.metaYield,
          'data-meta-type': d => d.metaType,
        });

      // bad metadata
      nodes
        .filter(d => d.metaType !== plateMetaDataType.OK)
        .append('rect')
        .attr({
          class: 'plateWell Marked',
          fill(d) { return getValidColor(d.phenotype, d.metaType); },
          id(d) { return `id${d.row}_${d.col}`; },
          'fill-opacity': '1',
          y(d) { return d.celStartY; },
          x(d) { return d.celStartX; },
          width: heatMapCelWidth,
          height: heatMapCelHeight,
          'data-col': d => d.col,
          'data-meta-gt': d => d.metaGT,
          'data-meta-gtWhen': d => d.metaGtWhen,
          'data-meta-yield': d => d.metaYield,
          'data-meta-type': d => d.metaType,
        });
    }


    dispatch2.on('setExp', setExperiment);
    dispatch2.on('reDrawExp', reDrawExperiment);
    const plateData = composeMetadata;
    const gHeatMap = g.selectAll('.rows')
      .data(plateData)
      .enter().append('g')
      .attr({
        'data-row': (_, i) => i,
      });

    const nodes = gHeatMap.selectAll('nodes')
      .data(d => d)
      .enter()
      .append('g')
      .attr('class', 'expNode')
      .on('mouseover', () => { onMouseOver(d3.select(this)); })
      .on('mouseout', () => { onMouseOut(d3.select(this)); })
      .on('click', (element) => { onClick(d3.select(this.parentNode), d3.select(this), element); });

    addShapes(nodes);
    addSymbols(nodes);

    if (displayLegend) {
      createLegend(g);
    }
  }

  function heatmap(container) {
    g = container;
    update();
  }

  heatmap.update = update;

  heatmap.data = (value) => {
    if (!arguments.length) return data;
    data = value;
    cols = data[0].length;
    rows = data.length;
    phenotypeMin = d3.min(data, array => d3.min(array));
    phenotypeMax = d3.max(data, array => d3.max(array));
    phenotypeMean = d3.mean(data, array => d3.mean(array));
    return heatmap;
  };

  heatmap.phenotypeName = (value) => {
    if (!arguments.length) return phenotypeName;
    phenotypeName = value;
    return heatmap;
  };

  heatmap.growthMetaData = (value) => {
    if (!arguments.length) return growthMetaData;
    growthMetaData = value;
    return heatmap;
  };

  heatmap.plateMetaData = (value) => {
    if (!arguments.length) return plateMetaData;
    plateMetaData = value;
    return heatmap;
  };

  heatmap.cellSize = (value) => {
    if (!arguments.length) return cellSize;
    cellSize = value;
    return heatmap;
  };

  heatmap.cellRadius = (value) => {
    if (!arguments.length) return cellRadius;
    cellRadius = value;
    heatMapCelHeight = value * 2;
    heatMapCelWidth = value * 2;
    return heatmap;
  };

  heatmap.colorScale = (value) => {
    if (!arguments.length) return colorScale;
    colorScale = value;
    return heatmap;
  };

  heatmap.colorSchema = (value) => {
    if (!arguments.length) return colorSchema;
    colorSchema = value;
    return heatmap;
  };

  heatmap.setColorScale = (value) => {
    if (typeof value === 'undefined' || value === null) {
      throw Error('colorSchema isundefined');
    }
    if (typeof data === 'undefined' || data === null) {
      throw Error('data is not set!');
    }

    colorSchema = value;
    const cs = d3.scale.linear()
      .domain([phenotypeMin, phenotypeMean, phenotypeMax])
      .range([colorSchema[0], colorSchema[1], colorSchema[2]]);
    colorScale = cs;
  };

  heatmap.margin = (value) => {
    if (!arguments.length) return margin;
    margin = value;
    return heatmap;
  };

  heatmap.displayLegend = (value) => {
    if (!arguments.length) return displayLegend;
    displayLegend = value;
    return heatmap;
  };

  heatmap.legendMargin = (value) => {
    if (!arguments.length) return legendMargin;
    legendMargin = value;
    return heatmap;
  };

  heatmap.legendWidth = (value) => {
    if (!arguments.length) return legendWidth;
    legendWidth = value;
    return heatmap;
  };

  heatmap.dispatch2 = (value) => {
    if (!arguments.length) return dispatch2;
    dispatch2 = value;
    return heatmap;
  };

  return d3.rebind(heatmap, dispatch, 'on');
};
