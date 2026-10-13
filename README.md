# C2ModRegistry

The Chivalry 2 mod and plugin registry consumed by UnchainedLauncher. GitHub
releases host pak and DLL assets; this repository stores indexed metadata,
dependencies, manifests, download URLs, hashes and sizes.

## Register a release

1. Follow the [mod setup](https://github.com/Chiv2-Community/zero-infra-mod-registry/blob/v1/docs/mod/README.md)
   or [plugin setup](https://github.com/Chiv2-Community/zero-infra-mod-registry/blob/v1/docs/plugin/README.md).
2. Publish a tagged release with the asset and metadata.
3. Open an issue using this repository's registration template, or use the
   [release-request action](https://github.com/Chiv2-Community/zero-infra-mod-registry/blob/v1/docs/plugin/release-requests.md).
4. Maintainers review and merge the generated approval PR. Every version requires
   approval. Correct failed requests and reply `retry` on the issue.

## Registry automation

Workflow files here define triggers, permissions, concurrency and destination
branches. Shared actions and workflows come from
[zero-infra-mod-registry](https://github.com/Chiv2-Community/zero-infra-mod-registry).

- Registration issues create validated approval PRs.
- Pull requests validate both databases and DLL downloads.
- Pushes to `main` validate and publish snapshots to `db` and the temporary
  `update-registry-format` compatibility branch.

See [registry setup and action inputs](https://github.com/Chiv2-Community/zero-infra-mod-registry/blob/v1/docs/registry/README.md).
Enable Actions PR creation in repository settings. Workflow references and
`tool_ref` use upstream `v1`. Update both together when changing versions.
