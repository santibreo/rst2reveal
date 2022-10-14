import os
from docutils import nodes
from docutils.parsers.rst import directives

from . import HAS_MATPLOTLIB, STATIC_PATH



def plot_directive(name, arguments, options, content, lineno,
                       content_offset, block_text, state, state_machine):

    # Check if matplotlib is installed
    if not HAS_MATPLOTLIB:
        return []

    from . import plt
    from matplotlib import tempfile

    # Process the options
    width = options.get('width', '75%')
    if not width.endswith('%'):
        print('Warning: Width must be a percentage, using: 80%')
        width = '80%'
    align = options.get('align', 'center')
    # Alpha
    try:
        alpha = options.get('alpha', 0)
        alpha = min(1, max(0, float(alpha)))
    except ValueError:
        print('Warning: alpha must be a floating value between 0.0 and 1.0')
        alpha = 0
    try:
        xkcd_magnitude = int(options.get('xkcd', 0))
    except ValueError:
        wrong = options['xkcd']
        print(f'Warning: the argument to :xkcd: must be a int, not {wrong!r}')
        xkcd_magnitude = 1
    # XKCD
    #if 'invert' in options.keys():
    #    plt.rcParams['figure.facecolor'] = 'b'
    #    plt.rcParams['figure.edgecolor'] = 'b'
    #    plt.rcParams['text.color'] = 'w'
    #    plt.rcParams['axes.edgecolor'] = 'w'
    #    plt.rcParams['axes.labelcolor'] = 'w'
    #    plt.rcParams['xtick.color'] = 'w'
    #    plt.rcParams['ytick.color'] = 'w'
    #    plt.rcParams['legend.frameon'] = False
    #    if not 'alpha' in options.keys(): # not specified, so default = 0.0
    #        alpha = 1

    # Execute the code line by line
    if xkcd_magnitude > 0:
        with plt.xkcd(xkcd_magnitude):
            fig, ax = plt.subplots()
    else:
        fig, ax = plt.subplots()

    for line in content:
        try:
            exec(line)
        except Exception as e:
            print('Error while executing matplotlib code:')
            print('    ', line)
            print(e)
            return []
    # Set dimensions
    #box_width, box_height = fig.get_size_inches() * 100
    box_width, box_height = 430, 350
    # Set transparency
    fig.patch.set_alpha(alpha)
    ax.patch.set_alpha(alpha)
    # Save the figure in a temporary SVG file
    temp_fd, temp_filepath = tempfile.mkstemp(
        suffix=".svg", dir=STATIC_PATH, text=True
    )
    os.close(temp_fd)
    fig.savefig(temp_filepath, dpi=600, transparent=True)
    # Optionally save the figure
    if 'save' in options.keys():
        fig.savefig(options['save'], dpi=600,  transparent=True)

    # Extract the generated data
    start = False
    text = f'<div class="align-{align}">\n'
    with open(temp_filepath, 'r') as infile:
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
    os.remove(temp_filepath)

    return [nodes.raw('matplotlib', text, format='html')]

plot_directive.content = 1
plot_directive.arguments = (0, 0, 0)
plot_directive.options = {'align': directives.unchanged, 'width': directives.unchanged, 'alpha': directives.unchanged, 'invert': directives.unchanged, 'xkcd': directives.unchanged, 'save': directives.unchanged}

directives.register_directive('matplotlib', plot_directive)
