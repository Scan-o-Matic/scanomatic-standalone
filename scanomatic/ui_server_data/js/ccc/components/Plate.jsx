import PropTypes from 'prop-types';
import React from 'react';

import CCCPropTypes from '../prop-types';

const COLONY_OUTLINE_RADIUS = 30;
const SELECTED_COLONY_MARKER_RADIUS = 40;
const SELECTED_COLONY_MARKER_COLOR = '#c82124';
const SELECTED_COLONY_MARKER_STROKE_WIDTH = 5;
const SCALE = 0.2;

export function drawCircle(canvas, x, y, radius, lineWidth = 1, strokeStyle = 'black') {
  const context = canvas.getContext('2d');
  context.beginPath();
  context.strokeStyle = strokeStyle;
  context.lineWidth = lineWidth;
  context.arc(x, y, radius, 0, 2 * Math.PI);
  context.stroke();
}

export default class Plate extends React.Component {
  componentDidMount() {
    this.updateCanvas();
  }

  componentDidUpdate() {
    this.updateCanvas();
  }

  updateCanvas() {
    const context = this.canvas.getContext('2d');
    const { width, height } = this.canvas;
    context.drawImage(this.props.image, 0, 0, width, height);
    context.scale(SCALE, SCALE);
    if (this.props.grid) {
      const [ys, xs] = this.props.grid;
      for (let row = 0; row < xs.length; row += 1) {
        for (let col = 0; col < xs[row].length; col += 1) {
          const x = xs[row][col];
          const y = ys[row][col];
          drawCircle(this.canvas, x, y, COLONY_OUTLINE_RADIUS);
        }
      }

      if (this.props.selectedColony) {
        const { row, col } = this.props.selectedColony;
        const x = xs[row][col];
        const y = ys[row][col];
        drawCircle(
          this.canvas,
          x,
          y,
          SELECTED_COLONY_MARKER_RADIUS,
          SELECTED_COLONY_MARKER_STROKE_WIDTH,
          SELECTED_COLONY_MARKER_COLOR,
        );
      }
    }
    context.scale(1 / SCALE, 1 / SCALE);
  }

  render() {
    return (
      <canvas
        width={this.props.image.width * SCALE}
        height={this.props.image.height * SCALE}
        ref={(canvas) => {
          this.canvas = canvas;
        }}
      />
    );
  }
}

Plate.propTypes = {
  image: PropTypes.instanceOf(Image).isRequired,
  grid: CCCPropTypes.gridShape,
  selectedColony: CCCPropTypes.selectedColonyShape,
};

Plate.defaultProps = {
  grid: undefined,
  selectedColony: undefined,
};
