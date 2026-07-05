package mztabm.definitions

import data.mztabm.config.id_references
import rego.v1

# METADATA
# title: Check missing targets referenced in MzTab-M sections
# description: Read id references and find missing targets
# custom:
#  policy_id: policy_d_0021
policy_d_0021 contains result if {
	meta := rego.metadata.rule()
	root := object.get(input, "root", object.get(input, "value", input))
	some config in id_references

	target_ids := target_ids_for_config(root, config)
	missing_ids := {id |
		some value in source_reference_values(root, config.source)
		some id in reference_values(value)
		not id in target_ids
	}

	count(missing_ids) > 0
	target := path_string(config.target)
	source := path_string(config.source)
	missing_ids_str := [text |
		some item in missing_ids
		text := sprintf("%v", [item])
	]
	ids_str := concat(", ", missing_ids_str)
	msg := sprintf("%v references %v %v but target items do not exist", [source, target, ids_str])

	result := {
		"policy_id": meta.custom.policy_id,
		"message": msg,
		"source": path_string(config.source),
	}
}

source_reference_values(root, source_path) := values if {
	parent_path := array.slice(source_path, 0, count(source_path) - 1)
	field := source_path[count(source_path) - 1]
	values := [value |
		some item in items_at_path(root, parent_path)
		is_object(item.value)
		value := object.get(item.value, field, null)
	]
}

target_ids_for_config(root, config) := target_ids if {
	target_ids := {id |
		some item in items_at_path(root, config.target)
		is_object(item.value)
		id := object.get(item.value, config.target_id_field, null)
		id != null
	}
}

items_at_path(root, path) := items if {
	count(path) == 1
	value := child_value(root, path[0])
	items := values_at_path(value, [path[0]])
}

items_at_path(root, path) := items if {
	count(path) == 2
	first := child_value(root, path[0])
	is_object(first)
	value := child_value(first, path[1])
	items := values_at_path(value, [path[0], path[1]])
}

items_at_path(root, path) := items if {
	count(path) == 2
	first := child_value(root, path[0])
	is_array(first)
	items := [item |
		some index, row in first
		value := child_value(row, path[1])
		item := {
			"path": [path[0], index, path[1]],
			"value": value,
		}
	]
}

values_at_path(value, path) := items if {
	is_array(value)
	items := [item |
		some index, row in value
		item := {
			"path": array.concat(path, [index]),
			"value": row,
		}
	]
}

values_at_path(value, path) := items if {
	not is_array(value)
	items := [{
		"path": path,
		"value": value,
	}]
}

reference_values(value) := refs if {
	refs := [ref |
		some ref in normalize_array(value)
		ref != null
	]
}

normalize_array(value) := value if is_array(value)

normalize_array(value) := [value] if not is_array(value)

child_value(root, key) := value if {
	is_object(root)
	value := object.get(root, key, null)
}

child_value(root, key) := value if {
	is_array(root)
	is_number(key)
	key >= 0
	key < count(root)
	value := root[key]
}

child_value(root, _) := null if {
	not is_object(root)
	not is_array(root)
}

path_string(path) := result if {
	result := concat("", [part_string(index, part) |
		some index, part in path
	])
}

part_string(_, part) := result if {
	is_number(part)
	result := sprintf("[%v]", [part])
}

part_string(index, part) := result if {
	is_string(part)
	index == 0
	result := part
}

part_string(index, part) := result if {
	is_string(part)
	index > 0
	result := sprintf(".%v", [part])
}
