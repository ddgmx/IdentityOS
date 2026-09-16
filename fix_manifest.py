import json

with open('registry/capabilities/browser/manifest.json', 'r') as f:
    data = json.load(f)

original_skills = list(data['skills'])
print('Original skills:', len(original_skills))

live_skills = [
    {'name': 'browser.live.status', 'description': 'Check live browser bridge connection status', 'permission': 'browser:live_read', 'effect': 'read', 'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False}},
    {'name': 'browser.live.list_tabs', 'description': 'List all tabs in the user live Firefox browser', 'permission': 'browser:live_tabs', 'effect': 'read', 'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False}},
    {'name': 'browser.live.active_tab', 'description': 'Get the currently active tab in the live browser', 'permission': 'browser:live_tabs', 'effect': 'read', 'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False}},
    {'name': 'browser.live.activate_tab', 'description': 'Activate a specific tab in the live browser', 'permission': 'browser:live_write', 'effect': 'write', 'input_schema': {'type': 'object', 'properties': {'tab_id': {'type': 'string', 'minLength': 1}}, 'additionalProperties': False, 'required': ['tab_id']}},
    {'name': 'browser.live.create_tab', 'description': 'Create a new tab in the live browser', 'permission': 'browser:live_write', 'effect': 'write', 'input_schema': {'type': 'object', 'properties': {'url': {'type': 'string'}}, 'additionalProperties': False}},
    {'name': 'browser.live.close_tab', 'description': 'Close a specific tab in the live browser', 'permission': 'browser:live_write', 'effect': 'write', 'input_schema': {'type': 'object', 'properties': {'tab_id': {'type': 'string', 'minLength': 1}}, 'additionalProperties': False, 'required': ['tab_id']}},
    {'name': 'browser.live.snapshot', 'description': 'Get a snapshot of a live browser tab', 'permission': 'browser:live_read', 'effect': 'read', 'input_schema': {'type': 'object', 'properties': {'tab_id': {'type': 'string', 'minLength': 1}, 'max_chars': {'type': 'integer'}}, 'additionalProperties': False, 'required': ['tab_id']}},
    {'name': 'browser.live.navigate', 'description': 'Navigate a live browser tab to a URL', 'permission': 'browser:live_write', 'effect': 'write', 'input_schema': {'type': 'object', 'properties': {'tab_id': {'type': 'string', 'minLength': 1}, 'url': {'type': 'string', 'minLength': 1}, 'wait_until': {'type': 'string'}}, 'additionalProperties': False, 'required': ['tab_id', 'url']},
    {'name': 'browser.live.click', 'description': 'Click an element in a live browser tab', 'permission': 'browser:live_write', 'effect': 'write', 'input_schema': {'type': 'object', 'properties': {'tab_id': {'type': 'string', 'minLength': 1}, 'selector': {'type': 'string', 'minLength': 1}}, 'additionalProperties': False, 'required': ['tab_id', 'selector']},
    {'name': 'browser.live.fill', 'description': 'Fill a form field in a live browser tab', 'permission': 'browser:live_write', 'effect': 'write', 'input_schema': {'type': 'object', 'properties': {'tab_id': {'type': 'string', 'minLength': 1}, 'selector': {'type': 'string', 'minLength': 1}, 'value': {'type': 'string'}}, 'additionalProperties': False, 'required': ['tab_id', 'selector', 'value']},
    {'name': 'browser.live.type', 'description': 'Type text into an element in a live browser tab', 'permission': 'browser:live_write', 'effect': 'write', 'input_schema': {'type': 'object', 'properties': {'tab_id': {'type': 'string', 'minLength': 1}, 'selector': {'type': 'string', 'minLength': 1}, 'text': {'type': 'string'}}, 'additionalProperties': False, 'required': ['tab_id', 'selector', 'text']},
    {'name': 'browser.live.press', 'description': 'Press a keyboard key in a live browser tab', 'permission': 'browser:live_write', 'effect': 'write', 'input_schema': {'type': 'object', 'properties': {'tab_id': {'type': 'string', 'minLength': 1}, 'key': {'type': 'string', 'minLength': 1}}, 'additionalProperties': False, 'required': ['tab_id', 'key']}
]

data['skills'] = data['skills'] + live_skills

with open('registry/capabilities/browser/manifest.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print('Updated manifest')
print('Total skills:', len(data['skills']))