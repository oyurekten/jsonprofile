package mztabm.definitions

import data.mztabm.config.column_counts
import rego.v1

# METADATA
# title: Validate column counts
# description: Verifies configured source item counts match the configured count_of item counts.
# custom:
#  policy_id: policy_d_0010
policy_d_0010 contains result if {
	meta := rego.metadata.rule()
	root := object.get(input, "root", object.get(input, "value", input))
	some config in column_counts

	source_path := source_actual_path(root, config.source)
	source := value_at_path(root, source_path)
	count_of := value_at_path(root, config.count_of)
	source_count := item_count(source)
	count_of_count := item_count(count_of)
	source_count != count_of_count

	msg = sprintf("'%v' has %v column(s) but '%v' has %v items", [path_string(source_path), source_count, path_string(config.count_of), count_of_count])

	result := {
		"policy_id": meta.custom.policy_id,
		"message": msg,
		"source": path_string(source_path)
	}
}

source_actual_path(_, source_path) := path if {
	path := source_path_candidates(source_path)[0]
}

source_actual_path(_, source_path) := path if {
	not source_has_index(source_path)
	path := source_path
}

source_path_candidates(source_path) := candidates if {
	source_has_single_index(source_path)
	strings := string_path_parts(source_path)
	index := number_path_parts(source_path)[0]
	candidates := [[strings[0], index, strings[1]]]
}

source_path_candidates(source_path) := [source_path] if {
	not source_has_index(source_path)
}

source_has_index(source_path) if {
	count(number_path_parts(source_path)) > 0
}

source_has_single_index(source_path) if {
	count(number_path_parts(source_path)) == 1
	count(string_path_parts(source_path)) == 2
}

string_path_parts(path) := parts if {
	parts := [part |
		some index, part in path
		is_string(part)
	]
}

number_path_parts(path) := parts if {
	parts := [part |
		some index, part in path
		is_number(part)
	]
}

value_at_path(root, path) := value if {
	count(path) == 0
	value := root
}

value_at_path(root, path) := value if {
	count(path) == 1
	value := child_value(root, path[0])
}

value_at_path(root, path) := value if {
	count(path) == 2
	value := child_value(child_value(root, path[0]), path[1])
}

value_at_path(root, path) := value if {
	count(path) == 3
	value := child_value(child_value(child_value(root, path[0]), path[1]), path[2])
}

value_at_path(root, path) := value if {
	count(path) == 4
	value := child_value(child_value(child_value(child_value(root, path[0]), path[1]), path[2]), path[3])
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

item_count(value) := count(value) if {
	is_array(value)
}

item_count(value) := count(value) if {
	is_object(value)
}

item_count(value) := 0 if {
	value == null
}

item_count(value) := 1 if {
	not is_array(value)
	not is_object(value)
	value != null
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
