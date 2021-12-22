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
    obj = $(obj);
    if (identifier == null || obj.id) {
      vals.push(obj.val());
    }
  });

  return vals[0];
}

export function SetSelectedGrayscale(name) {
  Execute(grayscaleSelectorClass, (obj) => {
    $(obj).val(name);
  });
}
