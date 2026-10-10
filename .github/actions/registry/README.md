# Registry integration

Uses `zero-infra-mod-registry` at `5577c4c3f5870f192c4929eaecc11ae6d7becf77` with `upstream.patch` applied before building. The patch preserves newline-delimited indexes and propagates validation/processing failures; the image cache key includes the patch hash.

Run the deterministic Docker/CLI regression suite with:

```sh
python3 -m unittest discover -s tests -v
```
