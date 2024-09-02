import { h, mount, OObject } from 'destam-dom'
import { Router } from 'destamatic-ui'

import Home from './pages/Home.jsx';

const routes = {
    '/': Home,
}

const Shared = OObject({})

let remove;
window.addEventListener('load', () => {
	remove = mount(document.body, <Router routes={routes} Shared={Shared}/>);
});

window.addEventListener('unload', () => remove());
