import webbrowser
import os
from biicode.common.utils import file_utils as fileUtils
import tempfile
from biicode.common.utils.bii_logging import logger
import json
from biicode.client.conf import BII_WEBURL, BII_WEBSTATIC  # url for loading html for graph
import urllib2
import urlparse


class Printer(object):
    def __init__(self, out_stream):
        """ The only parameter of the PRinter is an output stream. It is nonsense that a printer
        had access to the model or the factory
        """
        self.out = out_stream

    def print_find_result(self, find_result):
        logger.debug("FIND RESULT: %s" % str(find_result))
        if not find_result:
            return

        if find_result.resolved:
            self.out.success('Find resolved new dependencies:')
            for resolved in find_result.resolved:
                self.out.success('\t%s' % str(resolved))

        if find_result.unresolved:
            self.out.error('Find could not resolve:')
            for unresolved in find_result.unresolved:
                self.out.listitem('\t%s' % unresolved.name)
        #elif request.unresolved or find_result.updated:
        #    self.out.success('All dependencies resolved')

        if find_result.updated:
            self.out.success('Updated dependencies:')
            for dep in find_result.updated:
                self.out.success('\t%s\n' % str(dep))
        #elif not find_result.unresolved and not request.unresolved:
        #    self.out.write('Everything was up to date\n')

    def print_graph_hive_html(self, deps_tree):
        """Shows a dependencies graph visualization in the Web Browser"""

        temp_dir = tempfile.mkdtemp(suffix='biicode')
        temp_dir = os.path.join(temp_dir, 'report')
        if not os.path.isdir(temp_dir):
            os.mkdir(temp_dir)

        # Generate variables for filling template
        hive_json = json.dumps(deps_tree, sort_keys=True)
        # js_files = [BII_WEB_RESOURCES + "/static/js/graph/" + js for js in ['d3.helpers.js',
        #                                                                     'biiTree.js',
        #                                                                     'hive_graph.js']]
        # css_files = [BII_WEB_RESOURCES + "/static/css/graph/" + js for js in ['graph.css']]
        # legend_path = BII_WEB_RESOURCES + "/static/images/graph/graph_legend.svg"
        #
        # html_template = jinja_env.get_template("hive_graph_template.html")
        # html_file = html_template.render(json=hive_json,
        #                                  js_files=js_files,
        #                                  css_files=css_files,
        #                                  legend_path=legend_path)
        url = urlparse.urljoin(BII_WEBURL, 'widgets/graph?t=template')
        response = urllib2.urlopen(url)
        html_file = response.read()
        # now, paths to resources as css and js need to be update:
        html_file = html_file.replace("href=\"/static", "href=\"" + \
                                      urlparse.urljoin(BII_WEBSTATIC, "static"))
        html_file = html_file.replace("src=\"/static", "src=\"" + \
                                      urlparse.urljoin(BII_WEBSTATIC, "static"))
        # json dependencies information:
        html_file = html_file.replace("JSON_INFO", hive_json)
        # Save the graph html:
        html_path = os.path.join(temp_dir, 'hive_graph.html')
        fileUtils.save(html_path, html_file)
        self.out.info('Your hive graph has been saved in this location: %s' % html_path)
        self.out.info('Your hive dependencies graph will appear now in your default Web Browser')
        webbrowser.open('file:///' + html_path, new=2)  # new=2 open in a new tab, if possible
