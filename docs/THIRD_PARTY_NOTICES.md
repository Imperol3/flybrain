# Third-Party Notices

## `vaibhavkedarisetti/fruit-fly-lab` (GitHub)

Consulted during the design of this project as a technical/structural
reference (repository layout, which FlyWire files a similar pipeline
consumes, and to locate the correct published Shiu et al. 2024 LIF
constants — see `docs/BIOLOGICAL_ASSUMPTIONS.md`).

**License status:** this repository has no `LICENSE` file. Under GitHub's
Terms of Service, a public repository without an explicit license grants no
reuse rights beyond viewing the source on GitHub.com — it is effectively
all-rights-reserved. Accordingly:

- **No code was copied** from this repository into this project. Every
  module in `brain/`, `simulation/`, and `experiments/` here was written
  from scratch against the published model description and the V0 brief.
- **No prose/documentation text was copied.** Any factual content learned
  from that repository's own documentation (e.g., which numeric constants a
  cited paper reports, which file names a FlyWire download contains) is
  cited back to the primary source (the paper, or FlyWire/Codex) wherever
  possible, not attributed as this repository's original expression.
- If reuse rights are later clarified (e.g. a license is added upstream),
  this notice should be revisited before any code is reused.

## FlyWire FAFB v783 dataset

See `docs/DATA_PROVENANCE.md` for full attribution and license (CC
BY-NC-SA 4.0) details. The dataset itself is never redistributed by this
repository.

## Python dependencies

`numpy`, `scipy`, `pandas`, `pytest`, `fastapi`, `uvicorn`, `websockets`,
and the optional `brian2` are used under their respective open-source
licenses (BSD-3-Clause for numpy/scipy/pandas, MIT for FastAPI/uvicorn,
BSD for websockets, CeCILL for Brian2). No modifications are made to any of
these libraries.
