package mztabm.definitions

import data.mztabm.config.required_ids
import rego.v1

# METADATA
# title: Check undefined ids in MzTab-M sections
# description: Reports required id paths where the id value is null or undefined
# custom:
#  policy_id: policy_d_0020
policy_d_0020 contains result if {
	meta := rego.metadata.rule()
	root := object.get(input, "root", object.get(input, "value", input))

	violations := {violation |
		some config in required_ids
		some item in source_items(root, config.source)
		is_object(item.value)
		object.get(item.value, config.source_id_field, null) == null
		violation := path_string(array.concat(item.path, [config.source_id_field]))
	}

	count(violations) > 0
	ids := concat(", ", violations)
	msg := sprintf("Objects ids are undefined: '%v'", [ids])

	result := {
		"policy_id": meta.custom.policy_id,
		"message": msg,
		"source": "root",
	}
}

source_items(root, source_path) := items if {
	count(source_path) == 1
	value := child_value(root, source_path[0])
	items := values_at_path(value, [source_path[0]])
}

source_items(root, source_path) := items if {
	count(source_path) == 2
	first := child_value(root, source_path[0])
	is_object(first)
	value := child_value(first, source_path[1])
	items := values_at_path(value, [source_path[0], source_path[1]])
}

source_items(root, source_path) := items if {
	count(source_path) == 2
	first := child_value(root, source_path[0])
	is_array(first)
	items := [item |
		some index, row in first
		value := child_value(row, source_path[1])
		item := {
			"path": [source_path[0], index, source_path[1]],
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

child_value(root, key) := null if {
	is_array(root)
	is_number(key)
	key >= count(root)
}

child_value(root, key) := null if {
	is_array(root)
	is_number(key)
	key < 0
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
