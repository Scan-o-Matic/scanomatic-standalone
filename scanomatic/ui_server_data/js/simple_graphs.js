
function GetLinePlot(X, Y, Title, xLabel, yLabel) {
  const canvas = document.createElement('canvas');
  canvas.height = 200;
  canvas.width = 200;
  const padding = 20;
  const context = canvas.getContext('2d');
  X = FixValuesIn(X, padding, canvas.width - padding);
  Y = FixValuesIn(Y, padding, canvas.height - padding);
  DrawAxis(context, padding);

  DrawLine(context, X, Y, padding);

  if (xLabel) { GraphText(context, xLabel, null, canvas.height - padding / 1.5, 'horizontal', 10); }
  if (yLabel) { GraphText(context, yLabel, padding / 2, null, 'vertical', 10); }
  if (Title) { GraphText(context, Title, null, padding / 1.5, 'horizontal', 12); }

  return canvas;
}

function FixValuesIn(data, lower, upper) {
  const max = Math.max.apply(null, data);
  const scale = upper - lower;

  const fittedData = [];
  for (let i = 0, l = data.length; i < l; i++) { fittedData[i] = (data[i] / max) * scale; }

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
  for (let i = 0; i < l; i =+ 1) {
    if (i == 0) { context.moveTo(padding + X[i], context.canvas.height - (padding + Y[i])); } else { context.lineTo(padding + X[i], context.canvas.height - (padding + Y[i])); }
  }
  context.strokeStyle = 'green';
  context.stroke();
}

function GraphText(context, text, X, Y, orientation, size) {
  if (X == null) { X = context.canvas.width / 2; }
  if (Y == null) { Y = context.canvas.height / 2; }
  const lineheight = 15;
  const rotated = orientation.toLowerCase() === 'vertical';

  context.save();
  context.translate(X, Y);
  if (rotated) {
    context.rotate(-Math.PI / 2);
  }
  context.textAlign = 'center';
  context.font = `${size}pt Calibri`;
  context.fillStyle = 'black';
  context.fillText(text, 0, lineheight / 2);
  context.restore();
}
