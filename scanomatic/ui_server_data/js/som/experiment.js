import $ from 'jquery';
import {
  API,
  Dialogue,
  InputEnabled,
  getPathSuggestions,
} from './helpers';

let fixtureSelected = false;
let fixturePlates = [];
const descriptionCache = {};
let duration = [0, 0, 0];
let interval = 20.0;
let projectPath;
let projectPathValid = false;
let projectPathInvalidReason = '';
const poetry = "If with science, you let your life deteriorate,\nat least do it right.\nDo it with plight\nand fill out this field before it's too late";
const auxillaryInfo = {};
const auxillaryInfoTimeData = {};
let numberOfScans = -1;

function getValidationImage() {
  return "<img src='' class='icon-large'>";
}

function setValidationStatus(domObject, isValid, tooltip) {
  const input = $(domObject);
  let sib = input.next();
  if (sib.attr('class') !== 'icon-large') {
    sib = $(getValidationImage()).insertAfter(input);
  }

  if (isValid) {
    sib.attr('src', '/images/yeastOK.png').attr('alt', tooltip).attr('title', tooltip);
  } else {
    sib.attr('src', '/images/yeastNOK.png').attr('alt', tooltip).attr('title', tooltip);
  }
}

function getDurationAsMinutes() {
  return (((duration[0] * 24) + duration[1]) * 60) + duration[2];
}

export function validateExperiment() {
  setValidationStatus(
    '#project-path',
    projectPathValid,
    projectPathValid ? 'Everything is cool' : projectPathInvalidReason,
  );
  const scanner = $('#current-scanner');
  const scannerOK = scanner.val() !== '' && scanner.val() !== undefined && scanner.val() != null;
  setValidationStatus(scanner, scannerOK, scannerOK ? 'The scanner is yours' :
    'It would seem likely that you need a scanner... to scan');
  const activePlates = fixturePlates.filter(e => e.active).length > 0;
  let tooltip;
  if (!fixtureSelected) {
    tooltip = 'Select fixture';
  } else {
    tooltip = activePlates ? 'No plates active would mean doing very little' : 'All good!';
  }
  setValidationStatus('#current-fixture', fixtureSelected && activePlates, tooltip);
  const timeMakesSense = getDurationAsMinutes() >= 0;
  setValidationStatus(
    '#project-duration',
    timeMakesSense,
    timeMakesSense ? "That's a splendid project duration" : "Nope, you can't reverse time",
  );
  InputEnabled(
    $('#submit-button'),
    projectPathValid && scannerOK && fixtureSelected && activePlates && timeMakesSense,
  );
}

export function setPoetry(input) {
  $(input).html(poetry).css('font-style', 'italic');

  $(input).focus(() => {
    if ($(this).html() === poetry) { $(this).html('').css('font-style', 'normal'); }
  });

  $(input).blur(() => {
    if ($(this).html() === '') {
      $(this).html(poetry).css('font-style', 'italic');
    }
  });
}

export function setExperimentRoot(input) {
  getPathSuggestions(
    input,
    true,
    '',
    null,
    (data) => {
      projectPath = $(input).val();
      projectPathValid = data.valid_parent && !data.exists;
      projectPathInvalidReason = data.reason;

      setValidationStatus(
        '#project-path',
        projectPathValid,
        projectPathValid ? 'Everything is cool' : projectPathInvalidReason,
      );
      if (data.valid_parent && !data.exists) {
        $('#experiment-title').html(`Start Experiment '${data.prefix}'`);
      } else {
        $('#experiment-title').html('Start Experiment');
      }
    },
  );
}

function getDescription(index, description) {
  return `${"<div class='plate-description'>" +
        "<input type='hidden' value='"}${index}'>` +
        `<label for='plate-description-${index}'>Plate ${index}</label>` +
        `<input class='long' id='plate-description-${index}' value='${description
        }' placeholder='Enter medium and, if relevant, what experiment this plate is.' onchange='cacheDescription(this);'></div>`;
}

function setVisiblePlateDescriptions() {
  const activeIndices = $.map(fixturePlates
    .filter(value => value.active === true), entry => entry.index);

  const descriptions = $('#plate-descriptions');
  if (fixturePlates.length === 0) {
    descriptions.html('<em>Please, select a fixture and plate pinnings first.</em>');
    return;
  } descriptions.html('');

  for (let i = 0; i < activeIndices.length; i += 1) {
    const index = activeIndices[i];
    descriptions.append(getDescription(
      index,
      descriptionCache[index] !== undefined ? descriptionCache[index] : '',
    ));
  }
}

function getPlateSelector(plate) {
  return (
    `<div class='pinning'><input type='hidden' value='${plate.index}'>`
      + `<label for='pinning-plate-${plate.index}'>Plate ${plate.index}</label>`
      + `<select id='pinning-plate-${plate.index}' class='pinning-selector' onchange='setActivePlate(this); validateExperiment();'>`
        + '<option value=\'\'>Not used</option>'
        + '<option value=\'(8, 12)\'>8 x 12 (96)</option>'
        + '<option value=\'(16, 24)\'>16 x 24 (384)</option>'
        + '<option value=\'(32, 48)\' selected>32 x 48 (1536)</option>'
        + '<option value=\'(64, 96)\'>64 x 96 (6144)</option>'
      + '</select>'
    + '</div>'
  );
}

function getFixturePlateIndexOrdinal(index) {
  for (let i = 0; i < fixturePlates.length; i += 1) {
    if (fixturePlates[i].index === index) { return i; }
  }
  return -1;
}

function setPinningOptionsFromPlates(plates) {
  const activeIndices = $.map(plates, entry => entry.index);
  const pinnings = $('#pinnings');
  const pinningList = $('.pinning');

  if (plates.length === 0) {
    pinnings.html('<em>Please select a fixture first.</em>');
    return;
  } else if (pinningList.length === 0) {
    pinnings.html('');
  }

  pinningList.each(() => {
    const index = parseInt($(this).select("input[type='hidden']").val(), 10);
    if (!(index in activeIndices)) { $(this).remove(); } else {
      while (plates.length > 0 && plates[0].index <= index) {
        const plate = plates.shift();
        if (plate.index !== index) {
          $(this).before(getPlateSelector(plate));
        }
      }
    }
  });
  for (let i = 0; i < plates.length; i += 1) {
    pinnings.append(getPlateSelector(plates[i]));
    fixturePlates[getFixturePlateIndexOrdinal(plates[i].index)].active = true;
  }
}

export function updateFixture(options) {
  const fixture = $(options).val();

  $.get(`/api/data/fixture/get/${fixture}`, (data) => {
    if (data.success) {
      fixtureSelected = true;
    } else {
      data.plates = [];
      fixtureSelected = false;
    }
    fixturePlates = data.plates.slice();
    setPinningOptionsFromPlates(data.plates);
    setVisiblePlateDescriptions();
    validateExperiment();
  });
}

function getFixturePlateFromObj(obj) {
  return parseInt(obj.find("input[type='hidden']").val(), 10);
}

export function cacheDescription(target) {
  const index = getFixturePlateFromObj($(target).parent());
  descriptionCache[index] = $(target).val();
}

function getDescriptions() {
  const maxIndex = Math.max.apply(
    null,
    Object.keys(descriptionCache).map(item => parseInt(item, 10)),
  );

  const ret = [];

  for (let i = 0; i < maxIndex; i += 1) {
    ret[i] = descriptionCache[i + 1] !== undefined && fixturePlates[i].active
      ? descriptionCache[i + 1] : null;
  }

  return ret;
}

export function setActivePlate(plate) {
  const index = getFixturePlateIndexOrdinal(getFixturePlateFromObj($(plate).parent()));
  fixturePlates[index].active = $(plate).val() !== '';
  setVisiblePlateDescriptions();
}

export function formatTime(input) {
  const s = $(input).val();

  let days;
  try {
    days = parseInt(s.match(/(\d+) ?(days|d)/i)[1], 10);
  } catch (err) {
    days = 0;
  }

  let minutes;
  try {
    minutes = parseInt(s.match(/(\d+) ?(min|minutes?|m)/i)[1], 10);
  } catch (err) {
    minutes = 0;
  }

  let hours;
  try {
    hours = parseInt(s.match(/(\d+) ?(hours?|h)/i)[1], 10);
  } catch (err) {
    if (minutes === 0 && days === 0) {
      hours = parseFloat(s);
      if (Number.isNaN(hours)) {
        hours = 0;
      }
      minutes = Math.round((hours - Math.floor(hours)) * 60);
      hours = Math.floor(hours);
    } else {
      hours = 0;
    }
  }
  if (minutes > 59) {
    hours += Math.floor(minutes / 60);
    minutes %= 60;
  }
  if (hours > 23) {
    days += Math.floor(hours / 24);
    hours %= 24;
  }

  if (days === 0 && hours === 0 && minutes === 0) { days = 3; }

  duration = [days, hours, minutes];
  $(input).val(`${days} days, ${hours} hours, ${minutes} minutes`);
}

export function formatMinutes(input) {
  interval = parseFloat($(input).val());
  if (Number.isNaN(interval) || interval <= 0) {
    interval = 20.0;
  } else if (interval < 7) {
    interval = 7.0;
  }
  $(input).val(`${interval} minutes`);
}

function getPinnings() {
  const ret = [];
  $('.pinning').each((i, e) => {
    const idx = $(e).find('input[type=hidden]').first().val() - 1;
    if (fixturePlates[idx].active) {
      ret[idx] = $(e)
        .find('.pinning-selector').first().val()
        .match(/\d+/g)
        .map(elem => parseInt(elem, 10));
    } else { ret[idx] = null; }
  });

  return ret;
}

export function updateScans(paragraph) {
  numberOfScans = Math.floor(getDurationAsMinutes() / interval) + 1;
  $(paragraph).html(numberOfScans);
}

export function setAux(input, key) {
  auxillaryInfo[key] = $(input).val();
}

export function setAuxTime(input, key, factor) {
  if (auxillaryInfoTimeData[key] === undefined) { auxillaryInfoTimeData[key] = {}; }

  auxillaryInfoTimeData[key][factor] = parseFloat($(input).val());

  let total = 0;
  auxillaryInfoTimeData[key].forEach((k) => {
    total += parseFloat(k) * auxillaryInfoTimeData[key][k];
  });

  auxillaryInfo[key] = total;
}

export function StartExperiment(button) {
  InputEnabled($(button), false);
  const data = {
    number_of_scans: numberOfScans,
    time_between_scans: interval,
    project_path: projectPath,
    description: $('#project-description').val(),
    email: $('#project-email').val(),
    pinning_formats: getPinnings(),
    fixture: $('#current-fixture').val(),
    scanner: parseInt($('#current-scanner').val(), 10),
    plate_descriptions: getDescriptions(),
    cell_count_calibration_id: $('#ccc-selection').val(),
    auxillary_info: auxillaryInfo,
  };

  API.postJSON('/api/project/experiment', data)
    .then((response) => {
      Dialogue(
        'Experiment',
        `Experiment ${response.name} enqueued, now go `
        + 'get a cup of coffee and pat yourself on the back. Your work here is done.',
        '',
        '/status',
      );
    })
    .catch((reason) => {
      if (reason) {
        Dialogue(
          'Analysis', 'Analysis Refused',
          reason, false, button,
        );
      } else {
        Dialogue(
          'Analysis', 'Unexpected error', 'An error occurred processing request',
          false, button,
        );
      }
    });
}
