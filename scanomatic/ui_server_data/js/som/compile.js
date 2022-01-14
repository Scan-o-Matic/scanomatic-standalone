import $ from 'jquery';
import {
  API,
  Dialogue,
  getPathSuggestions,
  getSharedValue,
  InputEnabled,
} from './helpers';

let localFixture = false;
let path = '';
let projectPathValid = false;
const imageListDiv = null;

function toggleManualSelection(isManual) {
  if (isManual) {
    imageListDiv.find('#options').show();
    imageListDiv.find('#list-buttons').show();
  } else {
    imageListDiv.find('#options').hide();
    imageListDiv.find('#list-buttons').hide();
  }
}

export function toggleManualSelectionBtn(button) {
  toggleManualSelection($(button).prop('checked'));
}

function setImageSuggestions(imagePath) {
  // Only do stuff if path changed
  if (imageListDiv.find('#hidden-path').val() !== imagePath) {
    imageListDiv.find('#hidden-path').val(imagePath);

    imageListDiv.find('#manual-selection').prop('checked', false);

    const options = imageListDiv.find('#options');
    options.empty();

    $.get(`/api/compile/image_list/${path}`, (data) => {
      for (let i = 0; i < data.images.length; i += 1) {
        const rowClass = i % 2 === 0 ? 'list-entry-even' : 'list-entry-odd';
        const imageData = data.images[i];
        options.append((
          `<div class='${rowClass}'>${String(`00${imageData.index}`).slice(-3)}: `
          + `<input type='checkbox' id='image-data-${imageData.index}' checked='checked' value='${imageData.file}'>`
          + `<label class='image-list-label' for='image-data-${imageData.index}'>${imageData.file}</label></div>`
        ));
      }

      const noImageError = '<em>Not a project folder</em>';
      if (data.images.length === 0) {
        $('#fixture-error-message').html(noImageError).show();
      } else if ($('#fixture-error-message').html() === noImageError) {
        $('#fixture-error-message').html('').hide();
      }
    });
  } else {
    toggleManualSelectionBtn(imageListDiv.find('#manual-selection'));
  }
}

export function setFixtureStatus() {
  const callback = (data) => {
    if (!data.success) {
      $('#fixture-error-message').html(`<em>${data.reason}</em>`).show();
    } else {
      $('#fixture-error-message').hide();
    }
  };

  const errorCallback = () => {
    $('#fixture-error-message').html('<em>Fixture file missing</em>').show();
  };

  if (localFixture) {
    $.get(`/api/data/fixture/local/${path.substring(5, path.length)}`, callback).fail(errorCallback);
  } else {
    const fixt = $(getSharedValue('currentFixtureId')).val();
    if (fixt) {
      $.get(`/api/data/fixture/get/${fixt}`, callback).fail(errorCallback);
    } else {
      $('#fixture-error-message').hide();
    }
  }
}

function GetIncludedImageList(forceList) {
  let images = null;
  if (forceList || imageListDiv.find('#manual-selection').prop('checked')) {
    images = [];
    imageListDiv.find('#options').children().each(() => {
      const imp = $(this).find(':input');
      if (imp.prop('checked') === true) {
        images.push(imp.val());
      }
    });
  }
  return images;
}

export function setProjectDirectory(input) {
  getPathSuggestions(
    input,
    true,
    '',
    null,
    (data) => {
      path = $(input).val();
      projectPathValid = data.valid_parent && data.exists;

      if (projectPathValid) {
        setImageSuggestions(path);
        $('#project-directory-info').html(`Scan images in folder: ${GetIncludedImageList(true).length}`);
        InputEnabled(imageListDiv.find('#manual-selection'), true);
      } else {
        toggleManualSelection(false);
        $('#project-directory-info').html('<em>The project directory is the directory that contains the images that were scanned.</em>');
        InputEnabled(imageListDiv.find('#manual-selection'), false);
      }

      if (localFixture) {
        setFixtureStatus();
      }
      InputEnabled($('#submit-button'), projectPathValid);
    },
  );
}

export function setOnAllImages(included) {
  imageListDiv.find('#options').children().each(() => {
    $(this).find(':input').prop('checked', included);
  });
}

export function compileToggleLocalFixture(caller) {
  localFixture = $(caller).prop('checked');
  setFixtureStatus();
  InputEnabled($(getSharedValue('currentFixtureId')), !localFixture);
}

export function Compile(button) {
  InputEnabled($(button), false);

  const data = {
    local: localFixture ? 1 : 0,
    fixture: localFixture ? '' : $(getSharedValue('currentFixtureId')).val(),
    path,
    chain: $('#chain-analysis-request').is(':checked') ? 0 : 1,
    images: GetIncludedImageList(),
  };

  API.postJSON('/api/project/compile', data)
    .then(() => Dialogue('Compile', 'Compilation enqueued', '', '/status'))
    .catch((reason) => {
      if (reason) {
        Dialogue('Compile', 'Compilation Refused', reason, false, button);
      } else {
        Dialogue('Compile', 'Unexpected error', 'An error occurred processing the request.', false, button);
      }
    });
}
