# MM-003 deterministic synthetic screenshots

These six PNG files are deterministic renderings of only the
`model_input.observation.screenshot_regions` fields in the frozen MM-002 eval
suite. The standard-library renderer is
`fullcycle_bridge.mm003_baseline_protocol.render_case_png`; it uses an embedded
bitmap font, fixed 1280x900 RGB canvas, and deterministic PNG encoding.

The UIA-only cases have no image. Gold records are never read by the renderer
or included in model prompts. The frozen MM-003 preregistration binds every
image by path, byte count, and SHA-256.
