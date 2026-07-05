package mztabm.definitions

import data.mztabm.config.id_references
import rego.v1

# METADATA
# title: Check unreferenced targets in MzTab-M sections
# description: Reports target ids that are not referenced by their configured source fields
# custom:
#  policy_id: policy_d_0022
policy_d_0022 contains result if {
	meta := rego.metadata.rule()
	root := object.get(input, "root", object.get(input, "value", input))
	some config in id_references

	referenced_ids := referenced_ids_for_target(root, config)
	some target in unreferenced_targets(root, config, referenced_ids)
	source := sprintf("%v.%v", [path_string(target.path), config.target_id_field])
	msg := sprintf("%v id %v is not references in MzTab-M", [source, target.id])

	result := {
		"policy_id": meta.custom.policy_id,
		"message": msg,
		"source": source,
	}
}

unreferenced_targets(root, config, referenced_ids) := targets if {
	targets := [target |
		some item in items_at_path(root, config.target)
		is_object(item.value)
		id := object.get(item.value, config.target_id_field, null)
		id != null
		not id in referenced_ids
		target := {
			"path": item.path,
			"id": id,
		}
	]
}

referenced_ids_for_target(root, config) := referenced_ids if {
	referenced_ids := {id |
		some source_config in id_references
		source_config.target == config.target
		source_config.target_id_field == config.target_id_field
		some value in source_reference_values(root, source_config.source)
		some id in reference_values(value)
	}
}
