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

## D243 V2 standard selection

Pipe Design and the Pipe Size Library present a Turkish `Boru Standardı`
selector. EN 10220 is the default for new and legacy V1 project state. A pipe
recommendation and library table are always limited to the selected standard;
they never mix geometry from another standard. No ISO 1127 production data is
included until verified data is supplied.
