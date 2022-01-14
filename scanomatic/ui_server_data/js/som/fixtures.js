import $ from 'jquery';
import {
  clamp,
  Dialogue,
  getFixtureAsName,
  getFixtureFromName,
  getMousePosRelative,
  InputEnabled,
  isInt,
  unselect,
} from './helpers';
import {
  GetSelectedGrayscale,
  SetSelectedGrayscale,
} from './grayscales';
import GetLinePlot from './simple_graphs';
import { getSharedValue, setSharedValue } from '.';

let contextWarning = '';
let fixtureImage = null;
let fixtureName = null;
let markers = null;
let scale = 1;
let areas = [];
let creatingArea = null;
let selectedFixtureCanvas;
let grayscaleGraph = null;
let imageWidth = 0;
let imageHeight = 0;

function getPlate(plate) {
  if (isInt(plate)) {
    if (plate >= 0 && plate < areas.length) {
      return areas[plate];
    }
    return null;
  }
  return plate;
}

function isArea(index) {
  return index != null && index !== undefined && index >= 0 && index < areas.length;
}

function getAreaSize(plate) {
  const thePlate = getPlate(plate);

  if (thePlate) {
    return Math.abs(thePlate.x2 - thePlate.x1) * Math.abs(thePlate.y2 - thePlate.y1);
  }
  return -1;
}

function translateToImageCoords(coords) {
  const imageCoords = JSON.parse(JSON.stringify(coords));
  imageCoords.x = clamp(imageCoords.x, 0, imageWidth) / scale;
  imageCoords.y = clamp(imageCoords.y, 0, imageHeight) / scale;
  return imageCoords;
}

function hasGrayScale() {
  for (let len = areas.length, i = 0; i < len; i += 1) {
    if (areas[i].grayscale) { return true; }
  }
  return false;
}

function getAreaCenter(plate) {
  const thePlate = getPlate(plate);

  if (thePlate) {
    return {
      x: (thePlate.x1 + thePlate.x2) / 2,
      y: (thePlate.y1 + thePlate.y2) / 2,
    };
  }
  return {
    x: selectedFixtureCanvas.width / 2,
    y: selectedFixtureCanvas.height / 2,
  };
}


function setPlateIndices() {
  areas.sort((a, b) => {
    if (a.grayscale) {
      return -1;
    } else if (b.grayscale) {
      return 1;
    }

    if (a.y2 < b.y1) {
      return -1;
    } else if (b.y2 < a.y1) {
      return 1;
    } else if (a.x2 < b.x1) {
      return 1;
    } else if (b.x2 < a.x1) {
      return -1;
    }

    const aCenter = getAreaCenter(a);
    const bCenter = getAreaCenter(b);

    return aCenter.y < bCenter.y ? -1 : 1;
  });
  const len = areas.length;
  let plateIndex = 1;
  for (let i = 0; i < len; i += 1) {
    if (areas[i].grayscale !== true && areas[i].plate >= 0 && getAreaSize(i) > 0) {
      areas[i].plate = plateIndex;
      plateIndex += 1;
    }
  }
}

function drawMarker(context, centerX, centerY, radius, color, lineWidth) {
  context.beginPath();
  context.arc(centerX, centerY, radius, 0, 2 * Math.PI, false);
  context.lineWidth = lineWidth;
  context.strokeStyle = color;
  context.stroke();

  context.beginPath();
  context.moveTo(centerX - (0.5 * radius), centerY - (0.5 * radius));
  context.lineTo(centerX + (0.5 * radius), centerY + (0.5 * radius));
  context.moveTo(centerX + (0.5 * radius), centerY - (0.5 * radius));
  context.lineTo(centerX - (0.5 * radius), centerY + (0.5 * radius));
  context.lineWidth = 0.5 * lineWidth;
  context.strokeStyle = color;
  context.stroke();
}

function getUpdatedScale(canvas, obj) {
  const xScale = canvas.width / obj.width;
  const yScale = canvas.height / obj.height;
  return Math.min(scale, xScale, yScale);
}

function shadowText(context, area, textColor, shadowColor, text) {
  const fontSize = Math.min(area.x2 - area.x1, area.y2 - area.y1) * scale * 0.6;
  const center = getAreaCenter(area);

  context.font = `${fontSize * 1.1}pt Calibri`;
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillStyle = shadowColor;
  context.fillText(text, center.x * scale, center.y * scale);

  context.font = `${fontSize}pt Calibri`;
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillStyle = textColor;
  context.fillText(text, center.x * scale, center.y * scale);
}

function drawPlate(context, plate) {
  if (getAreaSize(plate) <= 0) {
    return;
  }
  context.beginPath();
  context.rect(
    plate.x1 * scale,
    plate.y1 * scale,
    (plate.x2 - plate.x1) * scale,
    (plate.y2 - plate.y1) * scale,
  );
  context.fillStyle = 'rgba(0, 255, 0, 0.1)';
  context.fill();
  context.strokeStyle = 'green';
  context.lineWidth = 2;
  context.stroke();

  let plateText;
  if (plate.grayscale) {
    plateText = 'G';
  } else {
    plateText = plate.plate < 0 ? '?' : plate.plate;
  }
  shadowText(context, plate, 'green', 'white', plateText);
}

export function drawFixture() {
  const canvas = selectedFixtureCanvas;
  const context = canvas.getContext('2d');

  context.clearRect(0, 0, canvas.width, canvas.height);

  if (fixtureImage) {
    scale = getUpdatedScale(canvas, fixtureImage);
    imageWidth = fixtureImage.width * scale;
    imageHeight = fixtureImage.height * scale;
    context.drawImage(fixtureImage, 0, 0, imageWidth, imageHeight);
  } else {
    imageWidth = 0;
    imageHeight = 0;
  }

  if (markers) {
    const radius = 140 * scale;
    const markerScale = 1;
    for (let len = markers.length, i = 0; i < len; i += 1) {
      drawMarker(
        context, markers[i][0] * scale * markerScale,
        markers[i][1] * scale * markerScale, radius, 'cyan', 3,
      );
    }
  }

  if (areas) {
    for (let i = 0; i < areas.length; i += 1) { drawPlate(context, areas[i]); }
  }

  if (grayscaleGraph) {
    const graphWidth = (canvas.width - imageWidth);
    context.drawImage(grayscaleGraph, imageWidth, 0, graphWidth, graphWidth);
  }

  if (contextWarning) {
    const canvasCenter = getAreaCenter(null);
    context.font = '20pt Calibri';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillStyle = 'red';
    context.fillText(contextWarning, canvasCenter.x, canvasCenter.y);
  }
}

function testAsGrayScale(plate) {
  const thePlate = getPlate(plate);

  if (thePlate) {
    const grayscaleName = GetSelectedGrayscale();
    $.ajax({
      url: `/api/data/grayscale/fixture/${fixtureName}?grayscale_name=${grayscaleName}`,
      method: 'POST',
      data: thePlate,
      success(data) {
        if (data.grayscale && hasGrayScale() === false) {
          thePlate.grayscale = true;
          grayscaleGraph = GetLinePlot(
            data.target_values, data.source_values,
            'Grayscale', 'Targets', 'Measured values',
          );
          InputEnabled($(getSharedValue('grayscaleTypeId')), false);
        } else {
          if (!hasGrayScale() && data.reason) {
            grayscaleGraph = GetLinePlot([], [], data.reason, 'Targets', 'Measured values');
          }
          thePlate.grayscale = false;
          thePlate.plate = 0;
          InputEnabled($(getSharedValue('grayscaleTypeId')), true);
          setPlateIndices();
        }
        drawFixture();
      },
      error() {
        contextWarning = 'Error occured detecting grayscale';
        setPlateIndices();
        drawFixture();
        InputEnabled($(getSharedValue('grayscaleTypeId')), true);
      },

    });
  }
}

function mouseUpFunction() {
  const minUsableSize = 10000;
  let curArea = creatingArea;
  creatingArea = null;
  if (isArea(curArea)) {
    const area = JSON.parse(JSON.stringify(areas[curArea]));
    const imagePos = translateToImageCoords({ x: imageWidth, y: imageHeight });
    area.x1 = Math.max(Math.min(areas[curArea].x1, areas[curArea].x2, imagePos.x), 0);
    area.x2 = Math.min(Math.max(areas[curArea].x1, areas[curArea].x2), imagePos.x);

    area.y1 = Math.max(Math.min(areas[curArea].y1, areas[curArea].y2, imagePos.y), 0);
    area.y2 = Math.min(Math.max(areas[curArea].y1, areas[curArea].y2), imagePos.y);
    areas[curArea] = area;
  }

  for (let i = 0; i < areas.length; i += 1) {
    if (getAreaSize(i) < minUsableSize) {
      if (areas[i] && areas[i].grayscale) {
        grayscaleGraph = null;
      }
      areas.splice(i, 1);
      if (i < curArea) {
        curArea -= 1;
      } else if (i === curArea) {
        curArea = -1;
      }
      i -= 1;
    }
  }

  if (curArea >= 0) {
    if (hasGrayScale()) {
      areas[curArea].plate = 0;
    } else {
      testAsGrayScale(curArea);
    }
  }
  setPlateIndices();
  drawFixture();
}


$(document.documentElement).mouseup((event) => {
  if (creatingArea != null && getSharedValue('selectedFixtureCanvasJq') != null) {
    mouseUpFunction(event);
  }
});

function isPointInArea(point, area) {
  return area.x1 < point.x && area.x2 > point.x && area.y1 < point.y && area.y2 > point.y;
}

function getAreaByPoint(point) {
  for (let len = areas.length, i = 0; i < len; i += 1) {
    if (isPointInArea(point, areas[i])) {
      return i;
    }
  }
  return -1;
}

function drawHoverSlice(imageCoords) {
  if (fixtureImage) {
    const canvas = selectedFixtureCanvas;
    const context = canvas.getContext('2d');

    const imageHalfSize = 90;
    const previewSize = 180;
    const cx = canvas.width - previewSize - 10;
    const cw = previewSize;
    const cy = canvas.height - cw - 10;
    const ch = cw;

    context.clearRect(cx, cy, ch, cw);

    const iw = (2 * imageHalfSize) + 1;
    const ix = Math.max(imageCoords.x - imageHalfSize, 0);

    const ih = (2 * imageHalfSize) + 1;
    const iy = Math.max(imageCoords.y - imageHalfSize, 0);

    context.drawImage(fixtureImage, ix, iy, iw, ih, cx, cy, cw, ch);
  }
}

export function setCanvas() {
  const canvas = $(getSharedValue('selectedFixtureCanvasId'));
  canvas.attr('tabindex', '0');

  canvas.mousedown((event) => {
    if (contextWarning) {
      contextWarning = null;
      return;
    }

    const canvasPos = getMousePosRelative(event, canvas);
    const imagePos = translateToImageCoords(canvasPos);
    creatingArea = null;
    const nextArea = getAreaByPoint(imagePos);
    if (event.button === 0) {
      if (nextArea < 0) {
        areas.push({
          x1: imagePos.x,
          x2: imagePos.x,
          y1: imagePos.y,
          y2: imagePos.y,
          grayscale: false,
          plate: -1,
        });
        creatingArea = areas.length - 1;
      } else {
        creatingArea = nextArea;
        if (areas[creatingArea].grayscale) { grayscaleGraph = null; }
        areas[creatingArea].x1 = imagePos.x;
        areas[creatingArea].y1 = imagePos.y;
        areas[creatingArea].x2 = imagePos.x;
        areas[creatingArea].y2 = imagePos.y;
        areas[creatingArea].grayscale = false;
        areas[creatingArea].plate = -1;
        InputEnabled($(getSharedValue('grayscaleTypeId')), true);
      }
    } else {
      if (areas[nextArea] && areas[nextArea].grayscale) {
        grayscaleGraph = null;
        InputEnabled($(getSharedValue('grayscaleTypeId')), true);
      }
      areas.splice(nextArea, 1);
      creatingArea = null;
    }
    drawFixture();
  });

  canvas.mousemove((event) => {
    const canvasPos = getMousePosRelative(event, canvas);
    const imagePos = translateToImageCoords(canvasPos);

    if (event.button === 0 && isArea(creatingArea)) {
      areas[creatingArea].x2 = imagePos.x;
      areas[creatingArea].y2 = imagePos.y;
      drawFixture();
    }

    drawHoverSlice(imagePos);
  });

  canvas.mouseup(mouseUpFunction);

  setSharedValue('selectedFixtureCanvasJq', canvas);
  setSharedValue('selectedFixtureCanvas', canvas[0]);
}

export function clearAreas() {
  areas = [];
  grayscaleGraph = null;
  contextWarning = '';
  InputEnabled($(getSharedValue('grayscaleTypeId')), true);
}

export function SetAllowDetect() {
  const disallow = $(getSharedValue('newFixtureImageId')).val() === ''
    || $(getSharedValue('newFixtureName')).val() === '';
  InputEnabled($(getSharedValue('newFixtureDetectId')), !disallow);
}

export function getFixtures() {
  const options = $(getSharedValue('currentFixtureId'));
  options.empty();
  $.get('/api/data/fixture/names', (data) => {
    $.each(data.fixtures, () => {
      options.append($('<option />').val(this).text(getFixtureAsName(this)));
    });
    unselect(options);
  });
  $(getSharedValue('newFixtureDataId')).hide();
  $(getSharedValue('selectedFixtureDivId')).hide();
}

export function addFixture() {
  const options = $(getSharedValue('currentFixtureId'));
  unselect(options);
  unselect($(getSharedValue('newFixtureImageId')));
  $(getSharedValue('saveFixtureActionId')).val('create');
  SetAllowDetect();
  $(getSharedValue('newFixtureDetectId')).val('Detect');
  $(getSharedValue('newFixtureDataId')).show();
  $(getSharedValue('selectedFixtureDivId')).hide();
}

function loadFixture(name) {
  fixtureName = name;
  $(getSharedValue('fixtureNameId')).text(getFixtureAsName(name));
  clearAreas();
  getSharedValue('selectedFixtureCanvasJq').focus();
  $(getSharedValue('selectedFixtureDivId')).show();
  drawFixture();
}

function loadFixtureImage(imageName) {
  if (imageName) {
    const img = new Image();
    img.onload = () => {
      fixtureImage = img;
      drawFixture();
    };
    img.src = `/api/data/fixture/image/get/${imageName}?rnd=${Math.random()}`;
  } else {
    fixtureImage = null;
  }
}

export function getFixture() {
  const options = $(getSharedValue('currentFixtureId'));
  $(getSharedValue('newFixtureDataId')).hide();
  $(getSharedValue('saveFixtureActionId')).val('update');
  loadFixture(options.val());
  loadFixtureImage(getFixtureFromName(options.val()));
  $.ajax({
    url: `/api/data/fixture/get/${options.val()}`,
    type: 'GET',
    success(data) {
      if (data.success) {
        areas.splice(0);
        for (let i = 0, l = data.plates.length; i < l; i += 1) {
          data.plates[i].grayscale = false;
          data.plates[i].plate = data.plates[i].index;
          areas.push(data.plates[i]);
        }
        data.grayscale.grayscale = true;
        data.grayscale.plate = -1;
        SetSelectedGrayscale(data.grayscale.name);
        InputEnabled($(getSharedValue('grayscaleTypeId')), false);

        areas.push(data.grayscale);
        ({ markers } = data);
      } else if (data.reason) {
        contextWarning = data.reason;
      } else {
        contextWarning = 'Unknown error retrieving fixture';
      }
      drawFixture();
    },
  });
}

function setFixtureMarkers(data) {
  ({ markers } = data);
  if (markers.length === 0) {
    markers = null;
    contextWarning = 'No markers were detected!';
    $(getSharedValue('newFixtureDataId')).show();
  }
  drawFixture();
}

export function detectMarkers() {
  const formData = new FormData();
  formData.append('markers', $(getSharedValue('newFixtureMarkersId')).val());
  formData.append('image', $(getSharedValue('newFixtureImageId'))[0].files[0]);
  InputEnabled($(getSharedValue('newFixtureDetectId')), false);
  const button = $(getSharedValue('saveFixtureButton'));
  InputEnabled(button, false);
  $(getSharedValue('newFixtureDetectId')).val('...');
  $.ajax({
    url: `/api/data/markers/detect/${$(getSharedValue('newFixtureName')).val()}`,
    type: 'POST',
    contentType: false,
    enctype: 'multipart/form-data',
    data: formData,
    processData: false,
    success(data) {
      loadFixture($(getSharedValue('newFixtureName')).val());

      if (data.image && data.markers) {
        contextWarning = '';
        $(getSharedValue('newFixtureDataId')).hide();
      } else {
        contextWarning = 'Name or image refused';
      }
      loadFixtureImage(data.image);
      setFixtureMarkers(data);
      InputEnabled(button, true);
    },
    error() {
      contextWarning = 'Marker detection failed';
      markers = null;
      loadFixture($(getSharedValue('newFixtureName')).val());
      drawFixture();
    },
  });
}

export function SaveFixture() {
  const button = $(getSharedValue('saveFixtureButton'));
  InputEnabled(button, false);
  const payload = {
    markers,
    grayscale_name: GetSelectedGrayscale(),
    areas,
  };
  $.ajax({
    url: `/api/data/fixture/set/${fixtureName}`,
    data: JSON.stringify(payload, null, '\t'),
    contentType: 'application/json;charset=UTF-8',
    dataType: 'json',
    processData: false,
    method: 'POST',
    success(data) {
      if (data.success) {
        $(getSharedValue('selectedFixtureDivId')).hide();
        Dialogue('Fixture', `Fixture "${fixtureName}" saved`, '', '?');
      } else {
        if (data.reason) {
          contextWarning = `Save refused: ${data.reason}`;
        } else {
          contextWarning = 'Save refused';
        }
        InputEnabled(button, true);
      }
      drawFixture();
    },
    error() {
      contextWarning = 'Crash while trying to save';
      drawFixture();
      InputEnabled(button, true);
    },
  });
}

export function RemoveFixture() {
  $('<div class=\'dialog\'></div>').appendTo('body')
    .html(`<div><h3>Are you sure you want to remove '${fixtureName}'?`)
    .dialog({
      modal: true,
      title: 'Remove',
      zIndex: 10000,
      autoOpen: true,
      width: 'auto',
      resizable: false,
      buttons: {
        Yes() {
          $.ajax({
            url: `/api/data/fixture/remove/${fixtureName}`,
            method: 'GET',
            success(data) {
              if (data.success) {
                $(getSharedValue('selectedFixtureDivId')).hide();
                Dialogue(
                  'Fixture', `Fixture "${fixtureName}" has been removed`,
                  '(A backup is always stored in the fixture config folder)', '?',
                );
              } else {
                if (data.reason) {
                  contextWarning = data.reason;
                } else {
                  contextWarning = 'Unknown removal issue';
                }
                drawFixture();
              }
            },
            error() {
              contextWarning = 'Crash while removing';
              drawFixture();
            },
          });
          $(this).dialog('close');
        },
        No() {
          $(this).dialog('close');
        },
      },
      close() {
        $(this).remove();
      },
    });
}
