
function getUrlParameter(sParam) {
  const sPageUrl = decodeURIComponent(window.location.search.substring(1));
  const sUrlVariables = sPageUrl.split('&');
  let sParameterName;

  for (let i = 0; i < sUrlVariables.length; i += 1) {
    sParameterName = sUrlVariables[i].split('=');

    if (sParameterName[0] === sParam) {
      return sParameterName[1] === undefined ? true : sParameterName[1];
    }
  }
  return null;
}

function FillPlate() {
  // 32x48
  let count = 0;
  const plate = d3.range(48).map(() => d3.range(32).map(() => {
    count += 1;
    return count;
  }));
  return plate;
}

function getLastSegmentOfPath(path) {
  const parts = path.split('/');
  let lastPart = parts.pop();
  if (lastPart === '') { lastPart = parts.pop(); }
  return lastPart;
}

function getExtentFromMultipleArrs() {
  if (!arguments.length) return null;
  const extremeValues = [];
  for (let i = 0; i < arguments.length; i++) {
    extremeValues.push(d3.max(arguments[i]));
    extremeValues.push(d3.min(arguments[i]));
  }
  const ext = d3.extent(extremeValues);
  return ext;
}

function getBaseLog(base, value) {
  return Math.log(value) / Math.log(base);
}
