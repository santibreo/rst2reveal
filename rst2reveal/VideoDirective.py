from docutils import nodes
from docutils.parsers.rst import directives

VIDEO_CODE = """\
            <div class="align-%(align)s">
                <video style="text-align:%(align)s; float:%(align)s" width="%(width)s" %(autoplay)s %(loop)s %(controls)s>
                      <source src="%(filename)s" type="video/%(codec)s">
                      Your browser does not support the video tag.
                </video>
            </div>
"""

VIDEO_CODECS = {
    "webm": "webm",
    "ogg": "ogg",
    "ogv": "ogg",
    "mp4": "mp4",
}


def video_directive(
    name, args, options, content, lineno, contentOffset, blockText, state, stateMachine
):
    """Restructured text extension for inserting videos"""
    if len(content) == 0:
        print("Error: no filename was provided to the video directive")
        return []
    # Check the type of the video
    filename = content[0]
    codec = VIDEO_CODECS.get(filename.split(".")[-1])
    if codec is None:
        print("ERROR: Video must be in .webm, .ogg, .ogv or .mp4 format.")
        return []

    # Process the arguments
    string_vars = {
        "filename": filename,
        "codec": codec,
        "width": "50%",
        "align": "center",
        "autoplay": "",
        "loop": "",
        "controls": "controls",
    }
    extra_args = content[1:]  # Because content[0] is ID
    args = {}
    import re

    for ea in extra_args:
        name = re.findall(r":(.+):", ea)[0]
        if len(re.findall(name + r":(.+)", ea)) > 0:
            value = re.findall(name + r":(.+)", ea)[0]
        else:
            value = ""
        args[name] = value
    if "width" in args.keys():
        string_vars["width"] = args["width"].strip()
    if "align" in args.keys():
        string_vars["align"] = args["align"].strip()
    if "autoplay" in args.keys():
        string_vars["autoplay"] = "autoplay"
    if "loop" in args.keys():
        string_vars["loop"] = "loop"
    #    if 'controls' in args.keys(): # TODO: no controls by default, but still clickable
    #        string_vars['controls'] = 'controls'

    return [nodes.raw("video", VIDEO_CODE % (string_vars), format="html")]


video_directive.content = True
directives.register_directive("video", video_directive)
