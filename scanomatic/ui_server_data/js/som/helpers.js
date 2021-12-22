export class API {
  static get(url) {
    return new Promise((resolve, reject) => $.ajax({
      url,
      type: 'GET',
      success: resolve,
      error: jqXHR => reject(JSON.parse(jqXHR.responseText).reason),
    }));
  }

  static postFormData(url, formData) {
    return new Promise((resolve, reject) => $.ajax({
      url,
      type: 'POST',
      contentType: false,
      enctype: 'multipart/form-data',
      data: formData,
      processData: false,
      success: resolve,
      error: jqXHR => reject(JSON.parse(jqXHR.responseText).reason),
    }));
  }

  static postJSON(url, json) {
    return new Promise((resolve, reject) => $.ajax({
      url,
      type: 'POST',
      data: JSON.stringify(json),
      contentType: 'application/json',
    })
      .then(
        resolve,
        jqXHR => reject(JSON.parse(jqXHR.responseText).reason),
      ));
  }
}

export function getPathSuggestions(input, isDirectory, suffix, suffixPattern, callback, prefix, checkHasAnalysis) {
  if (suffix === undefined) { suffix = ''; }

  let url;
  if (prefix !== undefined) {
    url = `${prefix.replace(/^\/?|\/?$/, '')}/${$(input).val().replace(/^\/?|\/?$/, '')}`;
  } else {
    url = $(input).val().replace(/^\/?|\/?$/, '');
  }

  if (url === '' || url === undefined) {
    url = '/api/tools/path';
  } else {
    url = `/api/tools/path/${url}`;
  }

  $.get(
    `${url}?suffix=${suffix
    }&isDirectory=${isDirectory ? 1 : 0
    }&checkHasAnalysis=${checkHasAnalysis ? 1 : 0}`,
    (data, status) => {
      const val = $(input).val();
      if (prefix) {
        const startIndex = (`root/${prefix.replace(/^\/?|\/?$/, '')}`).length;
        for (let i = 0; i < data.suggestions.length; i += 1) {
          data.suggestions[i] = data.suggestions[i].substring(startIndex, data.suggestions[i].length);
        }
      }

      if (suffixPattern != null) {
        const filtered = [];
        const filteredIsDirectories = [];
        let i = data.suggestions.length;
        while (i !== 0) {
          i -= 1;
          if (data.suggestion_is_directories[i] || suffixPattern.test(data.suggestions[i])) {
            filtered.push(data.suggestions[i]);
            filteredIsDirectories.push(data.suggestion_is_directories[i]);
          }
        }
        data.suggestions = filtered;
        data.suggestion_is_directories = filteredIsDirectories;
      }

      $(input).autocomplete({ source: data.suggestions });
      if (prefix == null && (val === '' || (data.path === 'root/' && val.length < data.path.length))) {
        $(input).val(data.path);
      }

      callback(data, status);
    },
  );
}

export function clamp(value, min, max) {
  if (value == null) {
    return min;
  }
  return Math.isNaN(value) ? max : Math.max(Math.min(value, max), min);
}

export function getMousePosRelative(event, obj) {
  return { x: event.pageX - obj.offset().left, y: event.pageY - obj.offset().top };
}

export function isInt(value) {
  return !Math.isNaN(value) &&
         parseInt(Number(value), 10) === value && !Math.isNaN(parseInt(value, 10));
}

export function InputEnabled(obj, isEnabled) {
  if (isEnabled) {
    obj.removeAttr('disabled');
  } else {
    obj.attr('disabled', true);
  }
}

export function unselect(target) {
  target.val('');
}

export function getFixtureAsName(fixture) {
  return fixture.replace(/_/g, ' ')
    .replace(/[^ a-zA-Z0-9]/g, '')
    .replace(
      /^[a-z]/g,
      $1 => $1.toUpperCase(),
    );
}

export function getFixtureFromName(fixture) {
  return `${fixture.replace(/ /g, '_')
    .replace(/[A-Z]/g, $1 => $1.toLowerCase())
    .replace(/[^a-z1-9_]/g, '')}.config`;
}

export function Execute(idOrClass, methodName) {
  $(idOrClass).each((i, obj) => {
    methodName($(obj));
  });
}

export function Dialogue(title, bodyHeader, body, redirect, reactivateButton) {
  $('<div class=\'dialog\'></div>').appendTo('body')
    .prop('title', title)
    .html(`<div>${bodyHeader != null ? (`<h3>${bodyHeader}</h3>`) : ''}${body != null ? body : ''}</div>`)
    .dialog({
      modal: true,
      buttons: {
        Ok() {
          $(this).dialog('close');
        },
      },
    })
    .on('dialogclose', () => {
      if (redirect) { location.href = redirect; }
      if (reactivateButton) { InputEnabled($(reactivateButton), true); }
    });
}

export function Map(arr, lambdaFunc) {
  const newArray = [];
  for (let i = 0; i < arr.length; i += 1) {
    newArray[i] = lambdaFunc(arr[i]);
  }
  return newArray;
}

export function setVersionInformation(target, preface) {
  API.get('/api/app/version')
    .then((data) => {
      let branch = '';
      if (data.source_information && data.source_information.branch) {
        branch = `, ${data.source_information.branch}`;
      }
      $(target).html(preface + data.version + branch);
    })
    .catch((reason) => {
      if (reason) {
        $(target).html(`Error checking version: ${reason}`);
      } else {
        $(target).html('Error checking version');
      }
    });
}
