# Build and release ZenSigil

This repository includes an offline playground build. The Python runtime has no
third-party dependencies. Building the UI requires Node and npm; building the wheel
requires setuptools and wheel in the build environment.

## Check and build

From the repository root:

```sh
python3 -m unittest discover -s tests -v
cd playground
npm ci
npm test
npm run build
cd ..
python3 -m unittest discover -s tests -v
python3 -m pip wheel --no-deps --wheel-dir dist .
```

The second Python run checks the freshly synchronized examples and browser assets.
The CI configuration targets Python 3.9 and 3.12 on Linux, macOS and Windows.
Configuration is not evidence of a remote CI run: inspect its actual results
after publishing the repository.

## Prove the wheel is independent of the checkout

Create a clean environment and install only the built wheel:

```sh
python3 -m venv /tmp/zensigil-release-check
/tmp/zensigil-release-check/bin/python -m pip install --no-index --no-deps --find-links dist zensigil
/tmp/zensigil-release-check/bin/python -I tools/verify_install.py
```

On Windows, use a temporary directory of your choice and
`ENV\Scripts\python.exe` for the environment's Python. `-I` isolates the check from
the checkout and user Python paths. The check exercises example scaffolding,
contracts, portable pack/run, namespace isolation, REPL rollback and expressions,
JUnit outcomes and module identities, editor startup, and installed HTTP resources.

## Package and verify

```sh
python3 tools/package_release.py dist
python3 tools/verify_release.py dist
```

The source ZIP excludes dependencies, Git internals and build caches. ZIP timestamps
and permissions are fixed, so the same source bytes and compression implementation
produce the same ZIP. The wheel is built separately and is not claimed to have a
reproducible hash across builds.

The SHA256SUMS file covers the source ZIP, fourteen portable examples, the local editor VSIX when present, and any wheel for
this version already in the destination. Hashes detect changes; a local checksum
file does not establish the identity of a publisher. Include it alongside the release.

## Public releases

Use the tested release candidate as the publication input. Before upload:

- Confirm the release destination is [zenoutlabs/zensigil](https://github.com/zenoutlabs/zensigil)
  and review the current repository state.
- Review the included files and license attribution.
- Push the tested source and inspect actual CI results.
- Tag the tested commit `v0.6.0` and attach the ZIP, wheel, examples and checksums to
  a GitHub release. Use the changelog as release notes.
- Add repository and release links to the project landing page and README.
- Publish the static introduction only after selecting a hosting destination.
  The Python playground server is a loopback development server, not a public host.

Package-registry publication is separate from the public source repository. Do not
tell users to `pip install zensigil` from a public registry until that package is
actually published and verified under the project's ownership. Install the local
wheel instead.

The landing page is `docs/index.html`. To preview it from the repository root:

```sh
python3 -m http.server 8767 --bind 127.0.0.1
```

Open http://127.0.0.1:8767/docs/index.html. This static introduction requires no
backend and includes documentation links. It does not execute ZenSigil.

See [launch-copy.md](launch-copy.md) for publication text and
[release-evidence-v06.md](release-evidence-v06.md) for the recorded verification and publication status.
