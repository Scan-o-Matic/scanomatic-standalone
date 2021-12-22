import $ from 'jquery';
import { Execute } from './helpers';

const grayscaleSelectorClass = '.grayscale-selector';

function getGrayscales(options) {
  options.empty();
  $.get('/api/data/grayscales', (data) => {
    if (data.grayscales) {
      for (let i = 0; i < data.grayscales.length; i += 1) {
        options.append($('<option></option>')
          .val(data.grayscales[i])
          .text(data.grayscales[i])
          .prop('selected', data.grayscales[i] === data.default));
      }
    }
  });
}

export function LoadGrayscales() {
  Execute(grayscaleSelectorClass, getGrayscales);
}

export function GetSelectedGrayscale(identifier) {
  const vals = [];
  $(grayscaleSelectorClass).each((i, obj) => {
    const o = $(obj);
    if (identifier == null || o.id) {
      vals.push(o.val());
    }
  });

  return vals[0];
}

export function SetSelectedGrayscale(name) {
  Execute(grayscaleSelectorClass, (obj) => {
    $(obj).val(name);
  });
}
