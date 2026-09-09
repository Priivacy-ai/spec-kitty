# Project doctrine entities

- Artifact: canonical kind, ID, source layer, project YAML path and content hash. Supported scope: directive, tactic, styleguide, procedure and agent_profile.
- DRG node: canonical URN, kind, label, project provenance.
- Reference edge: profile source URN to directive/tactic/procedure requires or styleguide suggests target URN; existing extractor owns mapping.
- Activation: charter.yaml selection IDs by canonical kind; planned state must validate before persistence.
- Provenance: source artifact identity and path recorded alongside synthesis manifest; user-authored sources remain authoritative.
- Glossary sense: normalized surface, owning scope, definition, confidence and status. List and show resolve the same seed store.
