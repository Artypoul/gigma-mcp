---
name: gigma-owner-project-ops
description: Safely inspect and manage owner workspaces, applications and client metadata.
---

# Owner project operations

Use discovered schemas from the active \`gigma\` server.

Read first:

- owner/workspace summary;
- application list and target application;
- service-client metadata when requested.

For writes:

- explain the intended change in plain language;
- ask for normal approval;
- use the current canonical resource name and ETag;
- use a request ID when the schema requires it;
- report the safe result;
- never retry an unknown one-time operation blindly.

Credentials and secrets remain on the trusted confidential channel. Show only safe
metadata such as whether credentials exist. The verified session determines the
workspace; never accept a user-supplied tenant switch.
