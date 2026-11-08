# Evidence-pack → CycloneDX ML-BOM / SPDX-AI field mapping

Phase 1 deliverable is the **mapping table only** (design §4.3, SPEC.md §7); the
converter is out of Phase 1 scope. This table shows how ReleaseSeal snapshot facts
and findings correspond to fields in the two emerging evidence containers so a
later exporter is a mechanical build, not a design task.

Standards referenced: CycloneDX 1.6 ML-BOM (`modelCard`, `components` of type
`machine-learning-model`) and SPDX 3.0 AI Profile (`AI_AIPackage`) + Core/Software.

## Release identity

| ReleaseSeal (snapshot) | CycloneDX ML-BOM | SPDX-AI |
|---|---|---|
| `source.repo_id` | `component.name` / `bom-ref` | `AIPackage.name` |
| `source.revision` | `component.version` | `Package.packageVersion` |
| `source.adapter` + capture | `metadata.properties["releaseseal:adapter"]` | `CreationInfo` comment |
| `snapshot_sha256` | `component.hashes[SHA-256]` (snapshot digest) | `Package.verifiedUsing` (Hash, SHA256) |
| `files[].path` / `.sha256` | `component.evidence` / `externalReferences` | `File.name` / `File.verifiedUsing` |

## Model-card facts

| ReleaseSeal | CycloneDX ML-BOM | SPDX-AI |
|---|---|---|
| `card.claims.license` | `component.licenses[].license.id` | `Package.licenseDeclared` |
| `card.claims.base_model[]` | `modelCard.modelParameters.datasets`/`components` dependency | `Relationship` type `DESCENDANT_OF` |
| `card.claims.base_model_relation` | `pedigree`/`property` | `Relationship` comment |
| `card.claims.param_count` | `modelCard.modelParameters.approach` props | `AIPackage.modelDataPreprocessing`/props |
| `card.claims.context_length` | `modelCard.modelParameters` property | `AIPackage` property |
| `config.model_type` | `modelCard.modelParameters.architectureFamily` | `AIPackage.typeOfModel` |
| `model_index` results | `modelCard.quantitativeAnalysis.performanceMetrics[]` | `AIPackage.metrics[]` |
| Annex XI/XII coverage (V4) | `modelCard.considerations` / `properties` | `AIPackage.informationAboutTraining` / `limitation` |

## Findings

A finding has no single native slot; it is evidence *about* the component.

| ReleaseSeal finding field | CycloneDX ML-BOM | SPDX-AI |
|---|---|---|
| `check` + `code` | `component.evidence.occurrences[].additionalContext` or `vulnerability`-style `property` key | `Annotation.annotationType=REVIEW`, subject = package |
| `severity` | `property["releaseseal:severity"]` | `Annotation` comment (severity prefix) |
| `message` | `property` value / occurrence note | `Annotation.statement` |
| `evidence.{file,field,expected,actual}` | `occurrences[].location` + context | `Annotation.statement` structured text |
| `heuristic` (V8) | `property["releaseseal:heuristic"]="true"` | `Annotation` comment flag |
| pack `chain_tip` | `metadata.properties["releaseseal:chain_tip"]` | `Element.extension` / `CreationInfo` comment |

## Notes

- ReleaseSeal findings are *review annotations*, not SPDX `vulnerabilities` /
  CycloneDX `vulnerabilities`; both standards model third-party review through
  annotations/evidence, which is the correct shape for documentation-consistency
  results (not security CVEs).
- The non-certification discipline carries over: exported annotations state
  consistency findings only and must not be relabelled as compliance attestations.
- Rule-pack versions travel as properties so a consumer can see which regulatory
  snapshot produced a V4 finding.
