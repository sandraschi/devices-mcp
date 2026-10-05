"""Label printer integrations (Supvan/Katasymbol, Dymo).

Pure protocol and rendering code lives here; MCP tools and web routes import from
this package and never talk to hardware directly.
"""

from .raster import LabelRenderError, render_text_label, to_mono

__all__ = ["LabelRenderError", "render_text_label", "to_mono"]
