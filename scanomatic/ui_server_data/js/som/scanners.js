import $ from 'jquery';
import { API, unselect } from './helpers';

export default function getFreeScanners(targetId) {
  const target = $(targetId);
  target.empty();
  API.get('/api/status/scanners/free')
    .then((data) => {
      $.each(data.scanners, (key, value) => {
        target.append($('<option />').val(key).text(value));
      });
      unselect(target);
    });
}
