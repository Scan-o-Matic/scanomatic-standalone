function FixValuesIn(data, lower, upper) {
  const max = Math.max.apply(null, data);
  const scale = upper - lower;

  const fittedData = [];
  for (let i = 0, l = data.length; i < l; i += 1) {
    fittedData[i] = (data[i] / max) * scale;
  }

  return fittedData;
}

function DrawAxis(context, padding) {
  context.beginPath();
  context.moveTo(padding, context.canvas.height - padding);
  context.lineTo(context.canvas.width - padding, context.canvas.height - padding);
  context.strokeStyle = 'black';
  context.stroke();

  context.beginPath();
  context.moveTo(padding, padding);
  context.lineTo(padding, context.canvas.height - padding);
  context.strokeStyle = 'black';
  context.stroke();
}

function DrawLine(context, X, Y, padding) {
  context.beginPath();
  const l = Math.min(X.length, Y.length);
  for (let i = 0; i < l; i += 1) {
    if (i === 0) {
      context.moveTo(padding + X[i], context.canvas.height - (padding + Y[i]));
    } else {
      context.lineTo(padding + X[i], context.canvas.height - (padding + Y[i]));
    }
  }
  context.strokeStyle = 'green';
  context.stroke();
}

function GraphText(context, text, X, Y, orientation, size) {
  const newX = X == null ? context.canvas.width / 2 : X;
  const newY = Y == null ? context.canvas.width / 2 : Y;
  const lineheight = 15;
  const rotated = orientation.toLowerCase() === 'vertical';

  context.save();
  context.translate(newX, newY);
  if (rotated) {
    context.rotate(-Math.PI / 2);
  }
  context.textAlign = 'center';
  context.font = `${size}pt Calibri`;
  context.fillStyle = 'black';
  context.fillText(text, 0, lineheight / 2);
  context.restore();
}

export default function GetLinePlot(X, Y, Title, xLabel, yLabel) {
  const canvas = document.createElement('canvas');
  canvas.height = 200;
  canvas.width = 200;
  const padding = 20;
  const context = canvas.getContext('2d');
  const fixedX = FixValuesIn(X, padding, canvas.width - padding);
  const fixedY = FixValuesIn(Y, padding, canvas.height - padding);
  DrawAxis(context, padding);

  DrawLine(context, fixedX, fixedY, padding);

  if (xLabel) {
    GraphText(context, xLabel, null, canvas.height - (padding / 1.5), 'horizontal', 10);
  }
  if (yLabel) {
    GraphText(context, yLabel, padding / 2, null, 'vertical', 10);
  }
  if (Title) {
    GraphText(context, Title, null, padding / 1.5, 'horizontal', 12);
  }

  return canvas;
}
