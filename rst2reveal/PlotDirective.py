from __future__ import annotations
import os
from typing import Union
from docutils import nodes
from docutils.parsers.rst import directives, Directive
from pathlib import Path

from . import HAS_MATPLOTLIB, STATIC_PATH
if HAS_MATPLOTLIB:
    from . import plt
    from matplotlib import tempfile


def align(argument: str):
    return directives.choice(argument, ('left', 'center', 'right'))

def width_percentage(argument: str):
    return str(directives.nonnegative_int(argument.strip()[:-1])) + "%"

def zero_to_one(argument: str):
    val = int(argument.strip())
    if not (0 <= val <= 1):
        raise ValueError(f"{argument} is not between 0 and 1")
    return val


class MatplotlibDirective(Directive):
    required_arguments = 0
    optional_arguments = 4
    final_argument_whitespace = True
    option_spec = {
        'align': align,
        'width': width_percentage,
        'alpha': zero_to_one,
        'xkcd': directives.flag
    }
    has_content = True
    node_class = nodes.raw

    @staticmethod
    def save_plot(
        code_as_text: str,
        fig: 'plt.Figure',
        ax: 'plt.Axes',
        alpha: float
    ) -> str:
        #  {{{
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
        temp_fd, temp_filepath = tempfile.mkstemp(
            suffix=".svg", dir=STATIC_PATH, text=True
        )
        os.close(temp_fd)
        fig.savefig(temp_filepath, dpi=600, transparent=True)
        return temp_filepath
        #  }}}

    def run(self):
        #  {{{
        # Raise an error if the directive does not have contents.
        self.assert_has_content()
        if not HAS_MATPLOTLIB:
            return []

        code = '\n'.join(self.content)
        alpha = self.options.get('alpha') or 0
        width = self.options.get('width') or '75%'
        xkcd = self.options.get('xkcd', '') is None
        align = self.options.get('align') or 'center'
        if xkcd:
            with plt.xkcd(1):
                fig, ax = plt.subplots()
                fig_path = self.save_plot(code, fig, ax, alpha)
        else:
            fig, ax = plt.subplots()
            fig_path = self.save_plot(code, fig, ax, alpha)
        # Insert image as svg
        if not fig_path:
            return []
        box_width, box_height = 430, 350
        start = False
        text = f'<div class="matplotlib-container r-stretch align-{align}">\n'
        with open(fig_path, 'r') as infile:
            for aline in infile:
                if aline.find('<svg ') != -1:
                    start = True
                    text += (
                        f'<svg width="{width}" '
                        f'viewBox="0 0 {box_width} {box_height}" '
                        'xmlns="http://www.w3.org/2000/svg >\n'
                    )
                elif start:
                    text += '  ' + aline
        text += '\n</div>\n'
        os.remove(fig_path)
        return [nodes.raw('matplotlib', text, format='html')]
        #  }}}

directives.register_directive('matplotlib', MatplotlibDirective)
