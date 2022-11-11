from __future__ import annotations
import os
import re
from pathlib import Path
from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives.images import Image
from docutils.parsers.rst.directives.body import CodeBlock
from typing import Union, Literal, Callable
from . import HAS_MATPLOTLIB, STATIC_TMP_PATH
from .transforms import HTMLAttributeTransform


if HAS_MATPLOTLIB:
    from . import plt
    NFIGS_CREATED = 0


def filename(argument: str) -> str:
    invalid_chars = r'~`!@\#$%^&*()="\';,.<>\\|/{}[]'
    fname = ''.join((x for x in argument if x not in invalid_chars))
    return fname


def zero_to_one(argument: str) -> int:
    val = int(argument.strip())
    if not (0 <= val <= 1):
        raise ValueError(f"{argument} is not between 0 and 1")
    return val


class CodeBlockDirective(CodeBlock):
    option_spec = CodeBlock.option_spec.copy()
    option_spec['linenos'] = directives.flag

    def run(self):
        self.state.document.settings.syntax_highlight = 'short'
        if self.options.pop('linenos', '') is None:
            self.options['number-lines'] = None
        return super().run()


class HTMLAttributeDirective(Directive):
    """
    Set a additional attributes on the next element. A "pending" element is
    inserted, and a transform does the work later.
    """

    required_arguments = 0
    optional_arguments = 10
    final_argument_whitespace = True
    has_content = False

    def run(self):
        try:
            html_attrs, vals_keys = {}, []
            for attr_info in self.arguments:
                if attr_info.startswith(":"):
                    if vals_keys:
                        html_attrs[vals_keys.pop(0)] = ''
                    vals_keys.append(attr_info.replace(':', ''))
                else:
                    html_attrs[vals_keys.pop(0)] = attr_info
            if vals_keys:
                html_attrs[vals_keys.pop(0)] = ''
        except ValueError:
            raise self.error(
                'Invalid attributes for "%s" directive: "%s".'
                % (self.name, ', '.join(self.arguments)))
        node_list = []
        pending = nodes.pending(HTMLAttributeTransform, html_attrs)
        self.state_machine.document.note_pending(pending)
        node_list.append(pending)
        return node_list


class MatplotlibDirective(Image):
    required_arguments: int = 0
    optional_arguments: int = 10
    final_argument_whitespace: bool = True
    option_spec: dict[str, Callable] = Image.option_spec.copy()
    option_spec['name']  = filename
    option_spec['alpha'] = zero_to_one
    option_spec['xkcd']  = directives.flag
    has_content: bool = True

    @property
    def temporary_filepath(self) -> str:
        #  {{{
        """Path to temporary SVG file to save plot """
        if not (fname := self.options.pop('name', '')):
            global NFIGS_CREATED
            NFIGS_CREATED += 1
            filepath = STATIC_TMP_PATH / f"matplot-{NFIGS_CREATED:04d}.svg"
        else:
            filepath = Path(STATIC_TMP_PATH / fname)
        return os.path.realpath(filepath.with_suffix(".svg"))
        #  }}}

    def save_plot(
        self,
        code_as_text: str,
        fig: 'plt.Figure',
        ax: 'plt.Axes',
        alpha: float
    ) -> Union[Path, Literal['']]:
        #  {{{
        """Saves plot defined from matplotlib code chunk"""
        unsafe_pattern = re.compile(r"\bimport\b (?!(numpy|pandas))")
        if re.search(unsafe_pattern, code_as_text):
            print('Error, your matplotlib code cannot contain "import" '
                  'statements. Only numpy and pandas are allowed.')
            return ''
        try:
            exec(code_as_text)
        except Exception as e:
            print('Error while executing matplotlib code:')
            print(*code_as_text.splitlines(), sep="\n\t")
            print(e)
            return ''
        # Set figure alpha
        fig.patch.set_alpha(alpha)
        ax.patch.set_alpha(alpha)
        # Save the figure in a temporary SVG file
        fig_path = self.temporary_filepath
        fig.savefig(fig_path, dpi=600, transparent=True)
        return Path(fig_path)
        #  }}}

    def run(self):
        #  {{{
        # Raise an error if the directive does not have contents.
        self.assert_has_content()
        if not HAS_MATPLOTLIB:
            return []
        code = '\n'.join(self.content)
        alpha = self.options.pop('alpha', 0)
        xkcd = self.options.pop('xkcd', '') is None
        if xkcd:
            fig_path = ""
            with plt.xkcd(1):
                fig, ax = plt.subplots()
                fig_path = self.save_plot(code, fig, ax, alpha)
        else:
            fig, ax = plt.subplots()
            fig_path = self.save_plot(code, fig, ax, alpha)
        # Insert image as svg
        if not fig_path:
            return []
        print(f"{fig_path} created!")
        # Prepare `self` to use Image directive
        self.content= ''
        self.arguments.append(f"static/img/{Path(fig_path).name}")
        self.options['align'] = self.options.get('align', 'center')
        node = super().run()[0]
        node.attributes['classes'].append('matplotlib-container')
        return [node]
        #  }}}

directives.register_directive('code-block', CodeBlockDirective)
directives.register_directive('html_attribute', HTMLAttributeDirective)
directives.register_directive('matplotlib', MatplotlibDirective)
