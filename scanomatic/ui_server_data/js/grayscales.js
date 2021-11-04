
const grayscale_selector_class = '.grayscale-selector';

function get_grayscales(options) {
  options.empty();
  $.get('/api/data/grayscales', (data, status) => {
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

function LoadGrayscales() {
  Execute(grayscale_selector_class, get_grayscales);
}

function GetSelectedGrayscale(identifier) {
  vals = [];
  $(grayscale_selector_class).each((i, obj) => {
    obj = $(obj);
    if (identifier == null || obj.id) { vals.push(obj.val()); }
  });

  return vals[0];
}

function SetSelectedGrayscale(name) {
  Execute(grayscale_selector_class, (obj) => {
    $(obj).val(name);
  });
}
