__docformat__ = 'reStructuredText'

import os
import re

from docutils import nodes
from docutils.writers.html4css1 import HTMLTranslator, Writer



class RST2RevealWriter(Writer):
    """ Writer to be used with the RevealTranslator class."""

    visitor_attributes = (
        'head_prefix', 'head', 'stylesheet', 'body_prefix',
        'body_pre_docinfo', 'docinfo', 'body', 'body_suffix',
        'title', 'subtitle', 'header', 'footer', 'meta', 'fragment',
        'html_prolog', 'html_head', 'html_title', 'html_subtitle',
        'html_body', 'metadata'
    )


class RST2RevealTranslator(HTMLTranslator):
    """
    Translator converting the reST items into HTML5 code usable by Reveal.js.

    Derived from docutils.writers.html4css1.HTMLTranslator.
    """

    def __init__(self, document):
        HTMLTranslator.__init__(self, document)
        self.math_output = 'mathjax'
        self.metadata = []
        self.is_subsection_previous = False
        self.inline_lists = False

    def starttag(self, node, tagname, suffix='\n', empty=False, **attributes):
        all_attributes = attributes | node.attributes.get('html_attributes', {})
        result = super().starttag(
            node, tagname, suffix, empty, **all_attributes
        )
        #print(result)
        return result

    def depart_header(self, node):
        start = self.context.pop()
        header = [self.starttag(node, 'section')]
        header.extend(self.body[start:])
        header.append('\n</section>\n')
        self.body_prefix.extend(header)
        self.header.extend(header)
        del self.body[start:]

    def visit_title(self, node):
        """Only 6 section levels are supported by HTML."""
        check_id = 0  # TODO: is this a bool (False) or a counter?
        close_tag = ' '*12 + '</p>\n'
        if isinstance(node.parent, nodes.topic):
            self.body.append(' '*12 +
                  self.starttag(node, 'p', '', CLASS='topic-title first'))
        elif isinstance(node.parent, nodes.sidebar):
            self.body.append(' '*12 +
                  self.starttag(node, 'p', '', CLASS='sidebar-title'))
        elif isinstance(node.parent, nodes.Admonition):
            self.body.append(' '*12 +
                  self.starttag(node, 'p', '', CLASS='admonition-title'))
        elif isinstance(node.parent, nodes.table):
            self.body.append(' '*12 +
                  self.starttag(node, 'caption', ''))
            close_tag = ' '*12 + '</caption>\n'
        elif isinstance(node.parent, nodes.document):
            self.body.append(' '*12 + self.starttag(node, 'h2', ''))
            close_tag = ' '*12 + '</h2>\n'
            self.in_document_title = len(self.body)
        else:
            assert isinstance(node.parent, nodes.section)
            self.body.append(' '*12 + self.starttag(node, 'h2', ''))
            close_tag = ' '*12 + '</h2>\n'
        self.context.append(close_tag)

    def depart_title(self, node):
        self.body.append(self.context.pop())
        if self.in_document_title:
            self.title = self.body[self.in_document_title:-1]
            self.in_document_title = 0
            self.body_pre_docinfo.extend(self.body)
            self.html_title.extend(self.body)
            del self.body[:]

    def visit_section(self, node):
        classes = node.attributes.get('classes', [])
        class_str = (
            ' class=' + ' '.join(map('"{}"'.format, classes))
            if classes else ''
        )
        attributes = node.attributes.get('html_attributes', {})
        attr_chunk = list()
        for attr, values in attributes.items():
            values = list(filter(lambda x: x!='', values))
            attr_vals = ('="' + ' '.join(values) + '"') if values else ''
            attr_chunk.append(attr + attr_vals)
        attr_str = ' ' + ' '.join(attr_chunk) if attributes else ''
        if self.section_level == 0:
            # Open new section
            self.body.append(' '*8 + f'<section{class_str}{attr_str}>\n')
        elif self.section_level == 1 and not self.is_subsection_previous:
            # First subsection needs to be closed at subsection opening
            self.is_subsection_previous = True
            self.body.append(' '*10 + f'</section>\n')
        # Open new subsection
        self.body.append(' '*10 + f'<section{class_str}{attr_str}>\n')
        self.section_level += 1

    def depart_section(self, node):
        # When section has subsections, subsection tag is closed at depart
        if not (self.section_level == 1 and self.is_subsection_previous):
            # Close subsection
            self.body.append(' '*10 + '</section>\n')
        if self.section_level == 1:
            # Close section
            self.is_subsection_previous = False
            self.body.append(' '*8 + '</section>\n')
        self.section_level -= 1
        self.inline_lists = False

    def visit_docinfo(self, node):
        self.context.append(len(self.body))
        self.in_docinfo = True

    def depart_docinfo(self, node):
        self.in_docinfo = False
        start = self.context.pop()
        self.docinfo = self.body[start:]
        self.body = []

    def visit_docinfo_item(self, node, name, meta=True):
        self.metadata.append(name + '=' + str(node)+'\n')
        self.body.append(self.starttag(node, 'tr', ''))
        if len(node):
            if isinstance(node[0], nodes.Element):
                node[0]['classes'].append('first')
            if isinstance(node[-1], nodes.Element):
                node[-1]['classes'].append('last')

    def depart_docinfo_item(self):
        pass

    def visit_field(self, node):
        pass

    def depart_field(self, node):
        pass

    def visit_field_body(self, node):
        field_names = re.findall(r'<field_name>(.+)</field_name>', str(node.parent[0]))
        field_values = re.findall(r'<field_body>(.+)</field_body>', str(node.parent[1]))
        if len(field_names) > 0 and len(field_values) > 0:
            name = field_names[0]
            value = field_values[0]
            self.metadata.append(name + '=' + value + '\n')

    def depart_field_body(self, node):
        pass

