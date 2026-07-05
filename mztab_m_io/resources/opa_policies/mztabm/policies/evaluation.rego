package mztabm.policies

import data.mztabm.definitions
import rego.v1

messages := [message |

	walk(definitions, [path, results])
	count(path) == 1
	name := path[0]

	startswith(name, input.policy_id)
	some result in results
    message = result
]
