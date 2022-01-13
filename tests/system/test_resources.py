import requests


class TestCommonResources:
    def test_own_js(self, scanomatic, browser):
        for js_file in (
            'ccc.js',
            'som.js',
        ):
            r = requests.get(scanomatic + '/js/somlib/{}'.format(js_file))
            r.raise_for_status()
            assert r.text and len(r.text), '{} is empty'.format(js_file)

    def test_images(self, scanomatic, browser):
        for im_file in (
            'favicon.ico',
            'stop.png',
            'menu.png',
            'yeastOK.png',
            'yeastNOK.png',
            'scan-o-matic_3.png',
        ):
            r = requests.get(scanomatic + '/images/{}'.format(im_file))
            r.raise_for_status()
            assert r.content and len(r.content), '{} is empty'.format(im_file)

    def test_css(self, scanomatic, browser):
        for css_file in (
            'analysis.css',
            'ccc.css',
            'compilation.css',
            'experiment.css',
            'fixtures.css',
            'logs.css',
            'main.css',
            'qc_norm.css',
            'status.css',
        ):
            r = requests.get(scanomatic + '/style/{}'.format(css_file))
            r.raise_for_status()
            assert r.text and len(r.text), '{} is empty'.format(css_file)
