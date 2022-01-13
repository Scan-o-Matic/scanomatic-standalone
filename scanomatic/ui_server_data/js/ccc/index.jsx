import React from 'react';
import ReactDOM from 'react-dom';
import 'bootstrap/dist/css/bootstrap.css';

import RootContainer from './containers/RootContainer';


$(document).ready(() => {
  ReactDOM.render(<RootContainer />, document.getElementById('react-root'));
});
