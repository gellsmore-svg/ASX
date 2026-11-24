# Integrations

These profiles are optional. The core package does not depend on Mahalath, Keturah, Deborah, Milcah, or SCL. Enabling a handler checks a payload grammar that was read from those projects on 2026-11-24. It does not call them.

An extension is an object:

```text
id        ASCII reverse-dns, version 1 for the profiles below
version   integer
critical  boolean
payload   bytes, at most 4096
```

Unknown critical extensions fail with `extension-critical-unknown`. Unknown noncritical extensions, and known profiles whose handlers are not enabled, are ignored. They are not bytes of the closed-set transcript.

| Profile | Payload grammar | What was observed | What ASX does not do |
| --- | --- | --- | --- |
| `org.gellsmore.mahalath.semantic-ref` | `mpl:<token>@<frame>#<64 lowercase hex>` | Mahalath publishes opaque `MPL-` labels and a frame. Retrieval is a separate CLI. | No MongoDB, no `mahalath retrieve`, no claim that Mahalath emits this digest today |
| `org.gellsmore.keturah.capability` | `product:<token> capability:<token>` | A Keturah capability has an ASCII name. `Manifest.to_mcp()` projects tools. | No import of Keturah, no registry lookup. If the handler is enabled, the operation must equal the capability token or the round halts |
| `org.gellsmore.deborah.process-ref` | `process:<token>` | Deborah stores process text and `BINDS` tokens. It does not resolve them. | No Cairn parse, no process runner. The token is a reference |
| `org.gellsmore.milcah.coherence` | `mode:(coherence\|research) terminal:(converged\|max_iterations\|no_objections\|insufficient_evidence\|blocked) ref:<64 hex>` | Those modes and terminal reasons are the Keturah envelope constants Milcah re-exports. Confidence is not a verdict. | No coherence run. The terminal reason is not a priority |

Default criticality for all four is false. A sender may mark one critical. If this process has not enabled that handler, the round stops. That is the ARB-16 rule: the core still ranks when the Deborah payload is noncritical and no adapter is loaded; a critical unknown adapter blocks.

There is no fifth, unnamed integration in the core. A deployment adds a handler only by shipping code that understands the id and version. The reference `screen_extensions` path enables a handler only when the caller lists it.
