# EN 10220 Pipe Size Library Dataset

YSH ships a local, offline EN 10220 reference dataset covering DN10 through
DN500. The data describes seamless and welded steel tube dimensions and masses
per unit length. Each row records `EN 10220` in the Standard field and the
dataset scope in its description.

The supplied source mapping is stored in
`database/en_10220_pipe_size_seed.py`. Inside diameter is derived for every row
as `OD − 2 × wall thickness`; no NPS or inch value is inferred from DN.

Reference: EN 10220, *Seamless and welded steel tubes — Dimensions and masses
per unit length*. Source mapping supplied for this YSH dataset:
https://blog.projectmaterials.com/pipe-valves-fittings-charts-pdf/pipe-en-10220/
