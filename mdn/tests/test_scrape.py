"""Test mdn.scrape."""
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from json import dumps

from parsimonious.grammar import Grammar

from mdn.models import FeaturePage, TranslatedContent
from mdn.scrape import (
    end_of_line, page_grammar, range_error_to_html, scrape_page,
    scrape_feature_page, slugify)
from webplatformcompat.models import (
    Browser, Feature, Maturity, Section, Specification)
from webplatformcompat.tests.base import TestCase


class TestGrammar(TestCase):
    def setUp(self):
        self.grammar = Grammar(page_grammar)

    def test_specdesc_td_empty(self):
        text = '<td></td>'
        parsed = self.grammar['specdesc_td'].parse(text)
        capture = parsed.children[2]
        self.assertEqual('', capture.text)

    def test_specdesc_td_plain_text(self):
        text = '<td>Plain Text</td>'
        parsed = self.grammar['specdesc_td'].parse(text)
        capture = parsed.children[2]
        self.assertEqual('Plain Text', capture.text)

    def test_specdesc_td_html(self):
        text = "<td>Defines <code>right</code> as animatable.</td>"
        parsed = self.grammar['specdesc_td'].parse(text)
        capture = parsed.children[2]
        self.assertEqual(
            'Defines <code>right</code> as animatable.', capture.text)


class ScrapeTestCase(TestCase):
    """Fixtures for scraping tests."""

    # Based on:
    # https://developer.mozilla.org/en-US/docs/Web/CSS/background-size?raw
    # but with fixes (id of <h2>, remove &nbsp;).
    simple_prefix = """\
<div>
 {{CSSRef}}</div>
"""
    simple_other_section = """\
<h2 id="Summary">Summary</h2>
<p>The <code>background-size</code> <a href="/en-US/docs/CSS" title="CSS">CSS\
</a> property specifies the size of the background images. The size of the\
 image can be fully constrained or only partially in order to preserve its\
 intrinsic ratio.</p>
<div class="note">
 <strong>Note:</strong> If the value of this property is not set in a\
 {{cssxref("background")}} shorthand property that is applied to the element\
 after the <code>background-size</code> CSS property, the value of this\
 property is then reset to its initial value by the shorthand property.</div>
<p>{{cssbox("background-size")}}</p>
"""
    simple_spec_section = """\
<h2 id="Specifications" name="Specifications">Specifications</h2>
<table class="standard-table">
 <thead>
  <tr>
   <th scope="col">Specification</th>
   <th scope="col">Status</th>
   <th scope="col">Comment</th>
  </tr>
 </thead>
 <tbody>
  <tr>
   <td>{{SpecName('CSS3 Backgrounds', '#the-background-size',\
 'background-size')}}</td>
   <td>{{Spec2('CSS3 Backgrounds')}}</td>
   <td></td>
  </tr>
 </tbody>
</table>
"""

    # From https://developer.mozilla.org/en-US/docs/Web/CSS/float?raw
    simple_compat_section = """\
<h2 id="Browser_compatibility">Browser compatibility</h2>
<div>
 {{CompatibilityTable}}</div>
<div id="compat-desktop">
 <table class="compat-table">
  <tbody>
   <tr>
    <th>Feature</th>
    <th>Chrome</th>
    <th>Firefox (Gecko)</th>
    <th>Internet Explorer</th>
    <th>Opera</th>
    <th>Safari</th>
   </tr>
   <tr>
    <td>Basic support</td>
    <td>1.0</td>
    <td>{{CompatGeckoDesktop("1")}}</td>
    <td>4.0</td>
    <td>7.0</td>
    <td>1.0</td>
   </tr>
  </tbody>
 </table>
</div>
<div id="compat-mobile">
 <table class="compat-table">
  <tbody>
   <tr>
    <th>Feature</th>
    <th>Android</th>
    <th>Firefox Mobile (Gecko)</th>
    <th>IE Mobile</th>
    <th>Opera Mobile</th>
    <th>Safari Mobile</th>
   </tr>
   <tr>
    <td>Basic support</td>
    <td>1.0</td>
    <td>{{CompatGeckoMobile("1")}}</td>
    <td>6.0</td>
    <td>6.0</td>
    <td>1.0</td>
   </tr>
  </tbody>
 </table>
</div>
"""
    # From Web/CSS/background-size?raw
    # colspan="3" on the Safari column
    # rowspan="2" on Basic Support row
    # footnotes with a <pre> section
    complex_compat_section = """\
<h2 id="Browser_compatibility" name="Browser_compatibility">\
Browser compatibility</h2>
<div>
 {{CompatibilityTable}}</div>
<div id="compat-desktop">
 <table class="compat-table">
  <tbody>
   <tr>
    <th>Feature</th>
    <th>Chrome</th>
    <th>Firefox (Gecko)</th>
    <th>Internet Explorer</th>
    <th>Opera</th>
    <th colspan="3">Safari (WebKit)</th>
   </tr>
   <tr>
    <td rowspan="2">Basic support</td>
    <td>1.0{{property_prefix("-webkit")}} [2]</td>
    <td>{{CompatGeckoDesktop("1.9.2")}}{{property_prefix("-moz")}} [4]</td>
    <td rowspan="2">9.0 [5]</td>
    <td>9.5{{property_prefix("-o")}}<br>
     with some bugs [1]</td>
    <td>3.0 (522){{property_prefix("-webkit")}}<br>
     but from an older CSS3 draft [2]</td>
   </tr>
   <tr>
    <td>3.0</td>
    <td>{{CompatGeckoDesktop("2.0")}}</td>
    <td>10.0</td>
    <td>4.1 (532)</td>
   </tr>
   <tr>
    <td>Support for<br>
     <code>contain</code> and <code>cover</code></td>
    <td>3.0</td>
    <td>{{CompatGeckoDesktop("1.9.2")}}</td>
    <td>9.0 [5]</td>
    <td>10.0</td>
    <td colspan="3">4.1 (532)</td>
   </tr>
   <tr>
    <td>Support for SVG backgrounds</td>
    <td>{{CompatUnknown}}</td>
    <td>{{CompatGeckoDesktop("8.0")}}</td>
    <td>{{CompatUnknown}}</td>
    <td>{{CompatUnknown}}</td>
    <td colspan="3">{{CompatUnknown}}</td>
   </tr>
  </tbody>
 </table>
</div>
<div id="compat-mobile">
 <table class="compat-table">
  <tbody>
   <tr>
    <th>Feature</th>
    <th>Android</th>
    <th>Firefox Mobile (Gecko)</th>
    <th>Windows Phone</th>
    <th>Opera Mobile</th>
    <th>Safari Mobile</th>
   </tr>
   <tr>
    <td>Basic support</td>
    <td>{{CompatVersionUnknown}}{{property_prefix("-webkit")}}<br>
     2.3</td>
    <td>1.0{{property_prefix("-moz")}}<br>
     4.0</td>
    <td>{{CompatUnknown}}</td>
    <td>{{CompatUnknown}}</td>
    <td>5.1 (maybe earlier)</td>
   </tr>
   <tr>
    <td>Support for SVG backgrounds</td>
    <td>{{CompatUnknown}}</td>
    <td>{{CompatGeckoMobile("8.0")}}</td>
    <td>{{CompatUnknown}}</td>
    <td>{{CompatUnknown}}</td>
    <td>{{CompatUnknown}}</td>
   </tr>
  </tbody>
 </table>
</div>
"""
    complex_compat_footnotes = """\
<p>[1] Opera 9.5's computation of the background positioning area is incorrect\
 for fixed backgrounds.  Opera 9.5 also interprets the two-value form as a\
 horizontal scaling factor and, from appearances, a vertical <em>clipping</em>\
 dimension. This has been fixed in Opera 10.</p>
<p>[2] WebKit-based browsers originally implemented an older draft of\
 CSS3<code> background-size </code>in which an omitted second value is treated\
 as <em>duplicating</em> the first value; this draft does not include\
 the<code> contain </code>or<code> cover </code>keywords.</p>
<p>[3] Konqueror 3.5.4 supports<code> -khtml-background-size</code>.</p>
<p>[4] While this property is new in Gecko 1.9.2 (Firefox 3.6), it is possible\
 to stretch a image fully over the background in Firefox 3.5 by using\
 {{cssxref("-moz-border-image")}}.</p>
<pre class="brush:css">.foo {
  background-image: url(bg-image.png);

  -webkit-background-size: 100% 100%;           /* Safari 3.0 */
     -moz-background-size: 100% 100%;           /* Gecko 1.9.2 (Firefox 3.6) */
       -o-background-size: 100% 100%;           /* Opera 9.5 */
          background-size: 100% 100%;           /* Gecko 2.0 (Firefox 4.0) and\
 other CSS3-compliant browsers */

  -moz-border-image: url(bg-image.png) 0;    /* Gecko 1.9.1 (Firefox 3.5) */
}</pre>
<p>[5] Though Internet Explorer 8 doesn't support the\
 <code>background-size</code> property, it is possible to emulate some of its\
 functionality using the non-standard <code>-ms-filter</code> function:</p>
<pre class="brush:css">-ms-filter:\
 "progid:DXImageTransform.Microsoft.AlphaImageLoader(\
src='path_relative_to_the_HTML_file', sizingMethod='scale')";</pre>
<p>This simulates the value <code>cover</code>.</p>
"""

    simple_see_also = """\
<h2 id="See_also">See also</h2>
<ul>
 <li>{{CSS_Reference:Position}}</li>
 <li><a href="/en-US/docs/Web/CSS/block_formatting_context">\
Block formatting context</a></li>
</ul>"""
    simple_page = (
        simple_prefix + simple_other_section + simple_spec_section +
        simple_compat_section + simple_see_also)
    complex_page = (
        simple_prefix + simple_other_section + simple_spec_section +
        complex_compat_section + complex_compat_footnotes + simple_see_also)

    def add_spec_models(self):
        self.maturity = self.create(
            Maturity, slug='CR', name='{"en": "Candidate Recommendation"}')
        self.spec = self.create(
            Specification, mdn_key='CSS3 Backgrounds',
            slug='css3_backgrounds', maturity=self.maturity,
            name='{"en": "CSS Backgrounds and Borders Module Level&nbsp;3"}',
            uri='{"en": "http://dev.w3.org/csswg/css3-background/"}')
        self.section = self.create(
            Section, specification=self.spec, name='{"en": "background-size"}',
            subpath='{"en": "#the-background-size"}')

    def add_compat_models(self):
        browsers = (
            ('Chrome', 'chrome'),
            ('Firefox', 'firefox'),
            ('Internet Explorer', 'ie'),
            ('Opera', 'opera'),
            ('Safari', 'safari'),
            ('Android', 'android'),
            ('Firefox Mobile', 'firefox-mobile'),
            ('IE Mobile', 'ie-mobile'),
            ('Opera Mobile', 'opera-mobile'),
            ('Safari Mobile', 'safari-mobile'),
        )
        self.browsers = dict()
        for name, slug in browsers:
            self.browsers[slug] = self.create(
                Browser, slug=slug, name={"en": name})

        if not hasattr(self, 'features'):
            self.add_compat_features()

    def add_compat_features(self):
        self.features = dict()
        self.features['web'] = self.create(
            Feature, slug='web', name={"en": "Web"})
        self.features['web-css'] = self.create(
            Feature, slug='web-css', name={"en": "CSS"},
            parent=self.features['web'])
        self.features['web-css-background-size'] = self.create(
            Feature, slug='web-css-background-size',
            name={"zxx": "background-size"})

    def add_models(self):
        self.add_spec_models()
        self.add_compat_models()


class TestEndOfLine(ScrapeTestCase):
    def test_middle_of_text(self):
        expected_eol = self.simple_page.index('\n', 30)
        end = end_of_line(self.simple_page, expected_eol - 2)
        self.assertEqual(expected_eol, end)

    def test_end_of_text(self):
        end = end_of_line(self.simple_page, len(self.simple_page) - 2)
        self.assertEqual(len(self.simple_page), end)


class TestScrape(ScrapeTestCase):
    longMessage = True

    def setUp(self):
        self.add_compat_features()

    def assertScrape(self, page, expected):
        """Specialize assertion for scraping"""
        actual = scrape_page(page, self.features['web-css-background-size'])
        exp_issues = expected.pop('issues')
        act_issues = actual.pop('issues')
        exp_errors = expected.pop('errors')
        act_errors = actual.pop('errors')
        self.assertDataEqual(expected, actual)
        self.assertEqual(len(exp_issues), len(act_issues), act_issues)
        self.assertEqual(len(exp_errors), len(act_errors), act_errors)
        for exp_issue, act_issue in zip(exp_issues, act_issues):
            self.assertEqual(
                exp_issue, act_issue, range_error_to_html(page, *act_issue))
        for exp_error, act_error in zip(exp_errors, act_errors):
            self.assertEqual(
                exp_error, act_error, range_error_to_html(page, *act_error))

    def test_empty(self):
        out = scrape_page("", self.features['web-css-background-size'])
        expected = {
            'locale': 'en',
            'specs': [],
            'compat': [],
            'footnotes': None,
            'issues': [],
            'errors': ["No <h2> found in page"],
        }
        self.assertDataEqual(out, expected)

    def test_spec_only(self):
        """Test with a only a Specification section."""
        expected = {
            'locale': 'en',
            'specs': [{
                'specification.mdn_key': 'CSS3 Backgrounds',
                'specification.id': None,
                'section.subpath': '#the-background-size',
                'section.name': 'background-size',
                'section.note': '',
                'section.id': None,
            }],
            'compat': [],
            'footnotes': None,
            'issues': [],
            'errors': [
                (251, 335, 'Unknown Specification "CSS3 Backgrounds"'),
            ]
        }
        self.assertScrape(self.simple_spec_section, expected)

    def test_simple_page(self):
        """Test with a more complete but simple page."""
        expected = {
            'locale': 'en',
            'specs': [{
                'specification.mdn_key': 'CSS3 Backgrounds',
                'specification.id': None,
                'section.subpath': '#the-background-size',
                'section.name': 'background-size',
                'section.note': '',
                'section.id': None,
            }],
            'compat': [{
                'name': 'desktop',
                'browsers': [
                    {
                        'name': 'Chrome',
                        'id': '_Chrome',
                    }, {
                        'name': 'Firefox',
                        'id': '_Firefox (Gecko)',
                    }, {
                        'name': 'Internet Explorer',
                        'id': '_Internet Explorer',
                    }, {
                        'name': 'Opera',
                        'id': '_Opera',
                    }, {
                        'name': 'Safari',
                        'id': '_Safari',
                    }],
                'features': [
                    {
                        'name': 'Basic support',
                        'id': '_Basic support',
                        'slug': 'web-css-background-size_basic_support',
                        'experimental': False,
                        'standardized': True,
                        'stable': True,
                        'obsolete': False,
                    }],
                'supports': [],
                'versions': [],
            }, {
                'name': 'mobile',
                'browsers': [
                    {
                        'name': 'Android',
                        'id': '_Android',
                    }, {
                        'name': 'Firefox Mobile',
                        'id': '_Firefox Mobile (Gecko)',
                    }, {
                        'name': 'IE Mobile',
                        'id': '_IE Mobile',
                    }, {
                        'name': 'Opera Mobile',
                        'id': '_Opera Mobile',
                    }, {
                        'name': 'Safari Mobile',
                        'id': '_Safari Mobile',
                    }],
                'features': [
                    {
                        'name': 'Basic support',
                        'id': '_Basic support',
                        'slug': 'web-css-background-size_basic_support',
                        'experimental': False,
                        'standardized': True,
                        'stable': True,
                        'obsolete': False,
                    }],
                'supports': [],
                'versions': [],
            }],
            'footnotes': None,
            'issues': [],
            'errors': [
                (902, 986, 'Unknown Specification "CSS3 Backgrounds"'),
                (1266, 1272, 'Unknown Browser "Chrome"'),
                (1286, 1301, 'Unknown Browser "Firefox (Gecko)"'),
                (1315, 1332, 'Unknown Browser "Internet Explorer"'),
                (1346, 1351, 'Unknown Browser "Opera"'),
                (1365, 1371, 'Unknown Browser "Safari"'),
                (1669, 1676, 'Unknown Browser "Android"'),
                (1690, 1712, 'Unknown Browser "Firefox Mobile (Gecko)"'),
                (1726, 1735, 'Unknown Browser "IE Mobile"'),
                (1749, 1761, 'Unknown Browser "Opera Mobile"'),
                (1775, 1788, 'Unknown Browser "Safari Mobile"'),
            ]
        }
        self.assertScrape(self.simple_page, expected)

    def test_simple_page_with_data(self):
        """Test with a simple page and data."""
        self.add_models()
        expected = {
            'locale': 'en',
            'specs': [{
                'specification.mdn_key': 'CSS3 Backgrounds',
                'specification.id': self.spec.id,
                'section.subpath': '#the-background-size',
                'section.name': 'background-size',
                'section.note': '',
                'section.id': self.section.id,
            }],
            'compat': [{
                'name': 'desktop',
                'browsers': [
                    {
                        'name': 'Chrome',
                        'id': self.browsers['chrome'].pk,
                    }, {
                        'name': 'Firefox',
                        'id': self.browsers['firefox'].pk,
                    }, {
                        'name': 'Internet Explorer',
                        'id': self.browsers['ie'].pk,
                    }, {
                        'name': 'Opera',
                        'id': self.browsers['opera'].pk,
                    }, {
                        'name': 'Safari',
                        'id': self.browsers['safari'].pk,
                    }],
                'features': [
                    {
                        'name': 'Basic support',
                        'id': '_Basic support',
                        'slug': 'web-css-background-size_basic_support',
                        'experimental': False,
                        'standardized': True,
                        'stable': True,
                        'obsolete': False,
                    }],
                'supports': [],
                'versions': [],
            }, {
                'name': 'mobile',
                'browsers': [
                    {
                        'name': 'Android',
                        'id': self.browsers['android'].pk,
                    }, {
                        'name': 'Firefox Mobile',
                        'id': self.browsers['firefox-mobile'].pk,
                    }, {
                        'name': 'IE Mobile',
                        'id': self.browsers['ie-mobile'].pk,
                    }, {
                        'name': 'Opera Mobile',
                        'id': self.browsers['opera-mobile'].pk,
                    }, {
                        'name': 'Safari Mobile',
                        'id': self.browsers['safari-mobile'].pk,
                    }],
                'features': [
                    {
                        'name': 'Basic support',
                        'id': '_Basic support',
                        'slug': 'web-css-background-size_basic_support',
                        'experimental': False,
                        'standardized': True,
                        'stable': True,
                        'obsolete': False,
                    }],
                'supports': [],
                'versions': [],
            }],
            'footnotes': None,
            'issues': [],
            'errors': [],
        }
        self.assertScrape(self.simple_page, expected)

    def test_complex_page_with_data(self):
        self.add_models()
        expected = {
            'locale': 'en',
            'specs': [{
                'specification.mdn_key': 'CSS3 Backgrounds',
                'specification.id': self.spec.id,
                'section.subpath': '#the-background-size',
                'section.name': 'background-size',
                'section.note': '',
                'section.id': self.section.id,
            }],
            'compat': [{
                'name': 'desktop',
                'browsers': [
                    {
                        'name': 'Chrome',
                        'id': self.browsers['chrome'].pk,
                    }, {
                        'name': 'Firefox',
                        'id': self.browsers['firefox'].pk,
                    }, {
                        'name': 'Internet Explorer',
                        'id': self.browsers['ie'].pk,
                    }, {
                        'name': 'Opera',
                        'id': self.browsers['opera'].pk,
                    }, {
                        'name': 'Safari',
                        'id': self.browsers['safari'].pk,
                    }],
                'features': [
                    {
                        'name': 'Basic support',
                        'id': '_Basic support',
                        'slug': 'web-css-background-size_basic_support',
                        'experimental': False,
                        'standardized': True,
                        'stable': True,
                        'obsolete': False,
                    }, {
                        'id': (
                            '_Support for<br>\n     <code>contain</code> and'
                            ' <code>cover</code>'),
                        'name': (
                            'Support for<br>\n     <code>contain</code> and'
                            ' <code>cover</code>'),
                        'slug': (
                            'web-css-background-size_support_for_br_code'
                            '_contai'),
                        'experimental': False,
                        'standardized': True,
                        'stable': True,
                        'obsolete': False,
                    }, {
                        'name': 'Support for SVG backgrounds',
                        'id': '_Support for SVG backgrounds',
                        'slug': (
                            'web-css-background-size_support_for_svg_'
                            'background'),
                        'experimental': False,
                        'standardized': True,
                        'stable': True,
                        'obsolete': False,
                    }],
                'supports': [],
                'versions': [],
            }, {
                'name': 'mobile',
                'browsers': [
                    {
                        'name': 'Android',
                        'id': self.browsers['android'].pk,
                    }, {
                        'name': 'Firefox Mobile',
                        'id': self.browsers['firefox-mobile'].pk,
                    }, {
                        'name': 'IE Mobile',
                        'id': self.browsers['ie-mobile'].pk,
                    }, {
                        'name': 'Opera Mobile',
                        'id': self.browsers['opera-mobile'].pk,
                    }, {
                        'name': 'Safari Mobile',
                        'id': self.browsers['safari-mobile'].pk,
                    }],
                'features': [
                    {
                        'name': 'Basic support',
                        'id': '_Basic support',
                        'slug': 'web-css-background-size_basic_support',
                        'experimental': False,
                        'standardized': True,
                        'stable': True,
                        'obsolete': False,
                    }, {
                        'name': 'Support for SVG backgrounds',
                        'id': '_Support for SVG backgrounds',
                        'slug': (
                            'web-css-background-size_support_for_svg_'
                            'background'),
                        'experimental': False,
                        'standardized': True,
                        'stable': True,
                        'obsolete': False,
                    }],
                'supports': [],
                'versions': [],
            }],
            'footnotes': self.complex_compat_footnotes,
            'issues': [],
            'errors': [],
        }
        self.assertScrape(self.complex_page, expected)

    def test_feature_slug_is_unique(self):
        self.add_models()
        collide = self.create(
            Feature, slug='web-css-background-size_basic_support',
            name={'en': 'Not Basic Support'})
        actual = scrape_page(
            self.simple_page,
            self.features['web-css-background-size'])
        self.assertNotEqual(
            str(collide.id),
            actual['compat'][0]['features'][0]['id'])
        self.assertEqual(
            'web-css-background-size_basic_support1',
            actual['compat'][0]['features'][0]['slug'])

    def test_parse_error(self):
        page = self.simple_page.replace("</h2>", "</h3")
        expected = {
            'locale': 'en',
            'specs': [],
            'compat': [],
            'footnotes': None,
            'issues': [],
            'errors': [
                (24, 52,
                 'Unable to finish parsing MDN page, starting at this'
                 ' position.')
            ]
        }
        self.assertScrape(page, expected)

    def test_with_issues(self):
        h2_fmt = '<h2 id="{0}" name="{0}">Specifications</h2>'
        h2_good = h2_fmt.format('Specifications')
        h2_bad = h2_fmt.format('Browser_Compatibility')
        self.assertTrue(h2_good in self.simple_spec_section)
        page = self.simple_spec_section.replace(h2_good, h2_bad)

        expected = {
            'locale': 'en',
            'specs': [{
                'specification.mdn_key': 'CSS3 Backgrounds',
                'specification.id': None,
                'section.subpath': '#the-background-size',
                'section.name': 'background-size',
                'section.note': '',
                'section.id': None,
            }],
            'compat': [],
            'footnotes': None,
            'issues': [
                (0, 79,
                 'In Specifications section, expected <h2 id="Specifications">'
                 ', actual id="Browser_Compatibility"'),
                (0, 79,
                 'In Specifications section, expected <h2'
                 ' name="Specifications"> or no name attribute,'
                 ' actual name="Browser_Compatibility"'),
            ],
            'errors': [
                (265, 349, 'Unknown Specification "CSS3 Backgrounds"'),
            ],
        }
        self.assertScrape(page, expected)


class TestScrapeFeaturePage(ScrapeTestCase):
    def setUp(self):
        self.add_models()
        url = ("https://developer.mozilla.org/en-US/docs/Web/CSS/"
               "background-size")
        self.page = FeaturePage.objects.create(
            url=url, feature=self.features['web-css-background-size'],
            status=FeaturePage.STATUS_PARSING)
        meta = self.page.meta()
        meta.raw = dumps({
            'locale': 'en-US',
            'url': url,
            'translations': [{
                'locale': 'fr',
                'url': url.replace('en-US', 'fr')
            }]})
        meta.status = meta.STATUS_FETCHED
        meta.save()

        for translation in self.page.translations():
            translation.status = translation.STATUS_FETCHED
            translation.raw = self.simple_page
            translation.save()

    def test_success(self):
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertEqual([], fp.data['meta']['scrape']['errors'])
        self.assertFalse(fp.has_issues)
        section_ids = [str(self.section.id)]
        self.assertEqual(section_ids, fp.data['features']['links']['sections'])

    def test_with_specification_mismatch(self):
        self.spec.mdn_key = 'CSS3_Backgrounds'
        self.spec.save()
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertTrue(fp.has_issues)
        self.assertEqual(
            ["_CSS3 Backgrounds_#the-background-size"],
            fp.data['features']['links']['sections'])

    def test_with_section_mismatch(self):
        self.section.subpath['en'] = '#the-other-background-size'
        self.section.save()
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertFalse(fp.has_issues)
        section_ids = ["%d_#the-background-size" % self.spec.id]
        self.assertEqual(section_ids, fp.data['features']['links']['sections'])

    def test_with_section_already_associated(self):
        self.page.feature.sections.add(self.section)
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertFalse(fp.has_issues)
        section_ids = [str(self.section.id)]
        self.assertEqual(section_ids, fp.data['features']['links']['sections'])

    def test_with_browser_mismatch(self):
        good_name = '<th>Chrome</th>'
        bad_name = '<th>Chromium</th>'
        en_content = TranslatedContent.objects.get(
            page=self.page, locale='en-US')
        self.assertEqual(1, en_content.raw.count(good_name))
        en_content.raw = en_content.raw.replace(good_name, bad_name)
        en_content.save()

        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertTrue(fp.has_issues)
        self.assertEqual(1, len(fp.data['meta']['scrape']['errors']))
        err = fp.data['meta']['scrape']['errors'][0]
        expected = '<div><p>Unknown Browser &quot;Chromium&quot;</p>'
        self.assertTrue(err.startswith(expected))
        desktop_browsers = fp.data['meta']['compat_table']['tabs'][0]
        self.assertEqual('Desktop', desktop_browsers['name']['en'])
        self.assertEqual('_Chromium', desktop_browsers['browsers'][0])

    def test_with_existing_feature(self):
        basic = self.create(
            Feature, slug=self.page.feature.slug + '-basic-support',
            name={'en': 'Basic support'}, parent=self.page.feature)
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertFalse(fp.has_issues)
        supports = fp.data['meta']['compat_table']['supports']
        self.assertTrue(str(basic.id) in supports)

    def test_scrape_almost_empty_page(self):
        en_content = TranslatedContent.objects.get(
            page=self.page, locale='en-US')
        en_content.raw = "<h1>nothing here</h1>"
        en_content.save()

        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertTrue(fp.has_issues)
        self.assertEqual(
            ["<pre>No &lt;h2&gt; found in page</pre>"],
            fp.data['meta']['scrape']['errors'])


class TestRangeErrorToHtml(ScrapeTestCase):
    def test_no_rule(self):
        html = range_error_to_html(
            self.simple_page, 902, 986,
            'Unknown Specification "CSS3 Backgrounds"')
        expected = """\
<div><p>Unknown Specification &quot;CSS3 Backgrounds&quot;</p>\
<p>Context:<pre>\
16  &lt;tbody&gt;
17   &lt;tr&gt;
18    &lt;td&gt;{{SpecName(&#39;CSS3 Backgrounds&#39;, &#39;#the-background-\
size&#39;, &#39;background-size&#39;)}}&lt;/td&gt;
**    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\
^^^^^^^^^^^^^^
19    &lt;td&gt;{{Spec2(&#39;CSS3 Backgrounds&#39;)}}&lt;/td&gt;
20    &lt;td&gt;&lt;/td&gt;
</pre></p></div>"""
        self.assertEqual(expected, html)

    def test_rule(self):
        html = range_error_to_html(
            self.simple_page, 902, 986,
            'Unknown Specification "CSS3 Backgrounds"',
            'me = "awesome"')
        expected = """\
<div><p>Unknown Specification &quot;CSS3 Backgrounds&quot;</p>\
<p><code>me = &quot;awesome&quot;</code></p>\
<p>Context:<pre>\
16  &lt;tbody&gt;
17   &lt;tr&gt;
18    &lt;td&gt;{{SpecName(&#39;CSS3 Backgrounds&#39;, &#39;#the-background-\
size&#39;, &#39;background-size&#39;)}}&lt;/td&gt;
**    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\
^^^^^^^^^^^^^^
19    &lt;td&gt;{{Spec2(&#39;CSS3 Backgrounds&#39;)}}&lt;/td&gt;
20    &lt;td&gt;&lt;/td&gt;
</pre></p></div>"""
        self.assertEqual(expected, html)


class TestSlugify(TestCase):
    def test_already_slugged(self):
        self.assertEqual('foo', slugify('foo'))

    def test_long_string(self):
        self.assertEqual(
            'abcdefghijklmnopqrstuvwxyz-abcdefghijklmnopqrstuvw',
            slugify('ABCDEFGHIJKLMNOPQRSTUVWXYZ-abcdefghijklmnopqrstuvwxyz'))

    def test_non_ascii(self):
        self.assertEqual('_', slugify("Рекомендация"))

    def test_limit(self):
        self.assertEqual(
            'abcdefghij', slugify('ABCDEFGHIJKLMNOPQRSTUVWXYZ', length=10))

    def test_num_suffix(self):
        self.assertEqual('slug13', slugify('slug', suffix=13))
