# PSIMiner (vendored, unmodified)

This directory contains the source of **PSIMiner** (Prefix-Sequence Inference
Miner), the timed temporal-logic mining engine used by this pipeline. It is
included here **verbatim and unmodified** for reproducibility.

- **Upstream:** https://github.com/antoniobruto/PSIMiner
- **Pinned commit:** `b0d03160a5a2aab00a43b31c3deb0e9036eb8ce4`
- **License:** GNU General Public License v3.0 (see `LICENSE` in this directory)
- **Authors:** Antonio A. Bruto da Costa and Pallab Dasgupta
  (see *"Learning Time-Delayed Interval Rules,"* JAIR 2021).

## Why it is here
The scripts in the top-level `code/` directory invoke the compiled `psiMiner`
binary as a **separate program** (via the shell / a subprocess); they do not
link against PSIMiner as a library. PSIMiner therefore remains a distinct
GPL-3.0 work aggregated alongside the MIT-licensed scripts, and its GPL license
governs this subdirectory only.

## Building
Only `code/`, `parsers/` (including `parsers/prefixes/`), and `build.sh` are
needed to build. From this directory:

```bash
bash build.sh          # requires a C compiler, flex, and bison
# produces build/psiMiner ; copy it next to the .conf files as ./psiMiner
```

The upstream `examples/` tree and prebuilt binaries are **not** vendored (they
are large and platform-specific); fetch them from upstream if needed.
