import $ from 'jquery';
import {
  API,
  Dialogue,
  getPathSuggestions,
  getSharedValue,
  InputEnabled,
  Map,
} from './helpers';

let gridplates = null;
let localFixture = true;
let path = '';

function appendRegriddingUI(parent, plateIndex) {
  parent.append((
    `<div class='plate-regridding' id='plate-regridding-${plateIndex}' onmouseleave='som.hideGridImage();'>`
      + '<fieldset>'
      + `<img class='grid_icon' src='/images/grid_icon.png' onmouseenter='som.loadGridImage(${plateIndex - 1});'>`
      + `<legend>Plate ${plateIndex}</legend>`

      + `<input type='radio' name='plate-regridding-radio-${plateIndex}' value='Keep' checked='checked'>`
      + `<label id='plate-regridding-keep${plateIndex}'>Keep previous</label><br>`

      + `<input type='radio' name='plate-regridding-radio-${plateIndex}' value='Offset'>`
      + `<label id='plate-regridding-offset-${plateIndex}'>Offset</label>`
      + `<input type='number' class='plate-offset' id='plate-regridding-offset-d1-${plateIndex}' value='0' name='Offset-d1'>`
      + `<input type='number' class='plate-offset' id='plate-regridding-offset-d2-${plateIndex}' value='0' name='Offset-d2'><br>`

      + `<input type='radio' name='plate-regridding-radio-${plateIndex}' value='New'>`
      + `<label id='plate-regridding-new-${plateIndex}'>New grid from scratch</label><br>`
      + '</fieldset>'
    + '</div>'
  ));
}

export function setFixturePlateListing() {
  const callback = (data) => {
    if (!data.success) {
      $('#fixture-error-message').html(`<em>${data.reason}</em>`).show();
    } else {
      $('#fixture-error-message').hide();
      gridplates = Map(data.plates, e => e.index);
      if ($('#manual-regridding').prop('checked')) {
        $('#manual-regridding-settings').show();
      } else {
        $('#manual-regridding-settings').hide();
      }
      const parent = $('#manual-regridding-plates');
      parent.empty();
      Map(gridplates, (e) => { appendRegriddingUI(parent, e); });
    }
  };

  const errorCallback = () => {
    $('#fixture-error-message').html('<em>Fixture file missing</em>').show();
  };

  if (localFixture) {
    if (path.length > 5) {
      $.get(`/api/data/fixture/local/${path.substring(5, path.length)}`, callback).fail(errorCallback);
    } else {
      errorCallback();
    }
  } else {
    const fixt = $(getSharedValue('currentFixtureId')).val();
    if (fixt) {
      $.get(`/api/data/fixture/get/${fixt}`, callback).fail(errorCallback);
    } else {
      $('#fixture-error-message').hide();
    }
  }
}

export function analysisToggleLocalFixture(caller) {
  localFixture = $(caller).prop('checked');
  InputEnabled($(getSharedValue('currentFixtureId')), !localFixture);
  setFixturePlateListing();
}

function getDir() {
  return $('#compilation').val().replace(/\/[^/]*$/, '');
}

let showGridImage = false;

export function hideGridImage() {
  showGridImage = false;
  $('#manual-regridding-image').hide();
}

export function loadGridImage(i) {
  showGridImage = true;
  const curDir = getDir();
  $('#manual-regridding-image').empty();
  $.get(
    `/api/results/gridding/${i}${curDir.substring(4, curDir.length)}/${$('#manual-regridding-source-folder').val()}`,
    (data) => {
      $('#manual-regridding-image').append(data.documentElement);
    },
  ).fail(() => {
    $('#manual-regridding-image').append("<p class='error-message'>Could not find the grid image! Maybe gridding failed last time?</p>");
  }).always(() => {
    if (showGridImage) {
      $('#manual-regridding-image').show();
    } else {
      hideGridImage();
    }
  });
}

function getRegriddingSetting(i) {
  const e = $(`#plate-regridding-${i}`);
  if (e.length !== 0) {
    switch (e.find(`input[name=plate-regridding-radio-${i}]:checked`).val()) {
    case 'Keep':
      return [0, 0];
    case 'Offset':
      return [
        parseInt(e.find(`#plate-regridding-offset-d1-${i}`).val(), 10),
        parseInt(e.find(`#plate-regridding-offset-d2-${i}`).val(), 10),
      ];

    case 'New':
      return null;
    default:
      return null;
    }
  } else {
    return null;
  }
}

function regriddingSettingsData() {
  const plates = [];
  if (gridplates != null) {
    const max = Math.max(...gridplates);
    for (let i = 1; i <= max; i += 1) {
      plates.push(getRegriddingSetting(i));
    }
  }
  return plates;
}

export function toggleManualRegridding(chkbox) {
  const isActive = $(chkbox).prop('checked');
  if (isActive) {
    setFixturePlateListing();
    $('#manual-regridding-settings').show();
  } else {
    $('#manual-regridding-settings').hide();
  }
}

export function setRegriddingSourceDirectory(input) {
  path = getDir();
  getPathSuggestions(
    input,
    true,
    '',
    null,
    (data) => {
      // TODO: For some reason popup doesn't appear...

      const regridCheckbox = $('#manual-regridding');
      regridCheckbox
        .prop('disabled', !data.has_analysis)
        .prop('checked', !!data.has_analysis);

      toggleManualRegridding(regridCheckbox);
    },
    path,
    true,
  );
}

export function setAnalysisDirectory(input, validate) {
  getPathSuggestions(
    input,
    true,
    '',
    null,
    (data) => {
      if (validate) {
        InputEnabled($('#submit-button2'), data.valid_parent && data.exists);
      }
    },
  );
}

export function setFilePath(input, suffix, suffixPattern, toggleRegriddingIfNotExists) {
  getPathSuggestions(
    input,
    true,
    suffix,
    suffixPattern,
    (data) => {
      if (toggleRegriddingIfNotExists) {
        $('#manual-regridding-source-folder').prop('disabled', !data.exists);
      }

      if (localFixture) {
        setFixturePlateListing();
      }
    },
  );
}

export function Analyse(button) {
  InputEnabled($(button), false);

  const data = {
    compilation: $('#compilation').val(),
    compile_instructions: $('#compile-instructions').val(),
    output_directory: $('#analysis-directory').val(),
    ccc: $('#ccc-selection').val(),
    chain: $('#chain-analysis-request').is(':checked') ? 0 : 1,
    one_time_positioning: $('#one_time_positioning').is(':checked') ? 0 : 1,
  };

  if ($('#manual-regridding').prop('checked')) {
    data.reference_grid_folder = $('#manual-regridding-source-folder').val();
    data.gridding_offsets = regriddingSettingsData();
  }

  API.postJSON('/api/project/analysis', data)
    .then(() => Dialogue('Analysis', 'Analysis Enqueued', '', '/status'))
    .catch((reason) => {
      if (reason) {
        Dialogue('Analysis', 'Analysis Refused', reason, false, button);
      } else {
        Dialogue('Analysis', 'Error', 'An error occurred processing request', false, button);
      }
    });
}

export function Extract(button) {
  InputEnabled($(button), false);

  API.postJSON(
    '/api/project/feature_extract',
    {
      analysis_directory: $('#extract').val(),
      keep_qc: $('#keep-qc').is(':checked') ? 0 : 1,
    },
  )
    .then(() => Dialogue('Feature Extraction', 'Extraction Enqueued', '', '/status'))
    .catch((reason) => {
      if (reason) {
        Dialogue('Feature Extraction', 'Extraction refused', reason, false, button);
      } else {
        Dialogue('Feature Extraction', 'Unexpected error', 'An error occurred processing request', false, button);
      }
    });
}

export function BioscreenExtract(button) {
  InputEnabled($(button), false);

  API.postJSON(
    '/api/project/feature_extract/bioscreen',
    {
      bioscreen_file: $('#bioscreen_extract').val(),
    },
  )
    .then(() => Dialogue('Feature Extraction', 'Extraction Enqueued', '', '/status'))
    .catch((reason) => {
      if (reason) {
        Dialogue('Feature Extraction', 'Extraction refused', reason, false, button);
      } else {
        Dialogue('Feature Extraction', 'Unexpected error', 'An error occurred processing request', false, button);
      }
    });
}

export function createSelector(elem) {
  $(elem).empty();
  $(elem).prop('disabled', true);
  $('#active-ccc-error').remove();

  $.getJSON('/api/calibration/active')
    .done((data) => {
      $.each(data.cccs, (i, item) => {
        $(elem).append($('<option>', {
          value: item.id ? item.id : '',
          text: `${item.species}, ${item.reference}`,
        }));
      });
      $(elem).prop('disabled', false);
    })
    .fail(() => {
      $(elem).after('<div class=\'error\' id=\'active-ccc-error\'>Could not retrieve CCCs</div>');
    });
}
