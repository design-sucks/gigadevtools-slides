"""Strict scope: reject global CSS at-rules and escaping; retain local authoring."""
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('maker_build',Path(__file__).with_name('build.py'))
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
invalid=['@property --sk-ink{syntax:"<color>";inherits:false;initial-value:red}', '@PrOpErTy --sk-ink{syntax:"*";inherits:false}', r'@\70 roperty --sk-ink{syntax:"*"}', '@font-face{font-family:x;src:url(x)}', '@layer shell{.x{color:red}}', '@keyframes/**/global{from{opacity:0}to{opacity:1}}', '.x} #bread {color:red}']
valid=['@media (min-width:1px){.x{color:red}}', '@supports (display:grid){.x{display:grid}}', '@keyframes gdslide-fade{from{opacity:0}to{opacity:1}} .x{animation:gdslide-fade 1s}', '.x::after{content:"@property"}']
for css in invalid:
 try:build.validate_scoped_css(css)
 except ValueError:continue
 raise AssertionError('Unsafe CSS accepted: '+css)
for css in valid:build.validate_scoped_css(css)
print('PASS: strict CSS rejects global registrations/escapes; accepts media, supports and namespaced animation')
