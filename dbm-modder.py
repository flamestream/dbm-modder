import sys
import json
import re
import os
import pathlib

SHORT_DESCRIPTION = 'Modifies DBM script to add custom yell notifier.'
LUA_COMMENT_LINE        = '-- FS-GENERATED'
LUA_COMMENT_START_BLOCK = '-- FS-GENERATED-START'
LUA_COMMENT_END_BLOCK   = '-- FS-GENERATED-END'
LUA_COMMENT_ORIGINAL    = '-- FS-GENERATED-COMMENTED'
DEFAULT_CONFIG_FILE = 'config.json'
DEFAULT_WOW_ADDON_DIR = str(os.path.normpath(os.path.join(pathlib.Path.home(), '..', 'Public', 'Games', 'World of Warcraft', 'Interface', 'Addons')))
DEFAULT_PREMONITION_SECONDS = 5
DEFAULT_PREMONITION_CHAT_CHANNEL = 'YELL'
DEFAULT_PREMONITION_CHAT_MESSAGE = r'%.0f seconds'
DEFAULT_EVENT_CHAT_CHANNEL = 'YELL'

def main(args):

	# Read command line
	config = parse_args(args)

	# Config/Error check
	if type(config) != dict:
		print('ERROR: %s' % config)
		print_help()
		return 1

	addon_dir = config.get('addonsDir', DEFAULT_WOW_ADDON_DIR)
	print('Looking for addon files at %s' % addon_dir)

	files = config['files'] or {}

	# Proceed away
	for file, definition_dict in files.items():

		# Load whole file in memory
		print('Processing %s...' % file)
		file_lines = None
		file_fullpath = os.path.normpath(os.path.join(addon_dir, file))
		try:

			with open(file_fullpath, 'r') as in_file:
				file_lines = in_file.read().splitlines()

		except FileNotFoundError:
			print('ERROR: DBM file not found. Ignoring definition set. (%s)' % file_fullpath)
			continue

		# Clean up
		remove_generated_code(file_lines)

		# Add (modified) rules
		if len(definition_dict):
			add_generated_code(definition_dict, file_lines)

		# Write back to file
		out_content = '\n'.join(file_lines)
		with open(file_fullpath, 'w', encoding='utf-8') as out_file:
			out_file.write(out_content)

# Display minimal help
def print_help():
	print("""
USAGE: python %s <config file>
""" % (__file__))

# Create config from arguments passed
def parse_args(args):

	arg_count = len(args)

	if arg_count <= 2:

		config_file = arg_count == 2 and args[1] or DEFAULT_CONFIG_FILE
		return load_config(config_file)

	else:
		return 'Invalid usage.'

# Load config file
def load_config(file):

	file_fullpath = os.path.abspath(file)
	print('Loading config file at %s' % file_fullpath)

	# JSON extension check
	if not file.endswith('.json'):
		return 'Config file must be a json file.'

	# Import config
	try:

		with open(file_fullpath) as json_data:
			return json.load(json_data)

	except FileNotFoundError:
		return 'Config file could not be found.'
	except json.decoder.JSONDecodeError as err:
		return 'Config JSON Parse Error: %s' % err

# --- LUA CODE GENERATORS --- #

def generate_premonition_yell_lua_code(timer_id, message, channel):

	return """
local function fs_yell_%s(premonitionTime)
	SendChatMessage(string.format("%s", premonitionTime), "%s")
end
local function fs_set_%s(self, targetTime, premonitionTime)
	self:Schedule(targetTime-premonitionTime, fs_yell_%s, premonitionTime)
end
local function fs_unset_%s(self)
	self:Unschedule(fs_yell_%s)
end
""" % (timer_id, message, channel, timer_id, timer_id, timer_id, timer_id)

def generate_set_premonition_yell_lua_code(indent, timer_id, target_seconds, premonition_seconds):

	return '%sfs_set_%s(self, %s, %s) %s' % (indent, timer_id, target_seconds, premonition_seconds, LUA_COMMENT_LINE)

def generate_unset_premonition_yell_lua_code(indent, timer_id):

	return '%sfs_unset_%s(self) %s' % (indent, timer_id, LUA_COMMENT_LINE)

def generate_comment_lua_code(line):

	return "--%s%s" % (line, LUA_COMMENT_ORIGINAL)

def generate_uncomment_lua_code(line):

	return line[2:-len(LUA_COMMENT_ORIGINAL)]

# --- LUA CODE PARSERS --- #

def parse_combat_event_register_lua_code(line):

	matches = re.match(r'[ \t]*"(\w+) (((\w+)\s*)+)",?', line)

	if not matches:
		print("  Error processing combat event register line: %s" % line)
		return '', []

	event_id = matches.group(1)
	spell_ids = set(matches.group(2).split(' '))
	return event_id, spell_ids

def parse_event_function_lua_code(line):

	matches = re.match(r'function mod:([^(]+)\(args\)', line)

	if not matches:
		print("  Error processing event function line: %s" % line)
		return

	event_id = matches.group(1)
	return event_id

def generate_event_chat_table_block_lua_code(event_definition_dict):

	out = 'local fs_chatArgsRegistry = {\n'

	for event_id, current_event_definition_dict in event_definition_dict.items():

		out += '\t%s = {\n' % event_id
		for spell_id, spell_event_definition_dict in current_event_definition_dict.items():

			channel = spell_event_definition_dict.get('channel', DEFAULT_EVENT_CHAT_CHANNEL)
			message = spell_event_definition_dict.get('fullMessage')
			if not message:
				label = current_event_definition_dict.get('alias', spell_id)
				desc = current_event_definition_dict.get('message', event_id)
				message = '[%s] %s' % (label, desc)

			out += '\t\t[%s] = {"%s", "%s"},\n' % (spell_id, message, channel)
		out += '\t},\n'
	out += '}\n'

	return out

def generate_event_block_lua_code(event_id):

	out = '''
	fs_args = fs_chatArgsRegistry["%s"][args.spellId]
	if fs_args then SendChatMessage(fs_args[1], fs_args[2]) end
''' % event_id

	out = '%s\n%s\n%s' % (LUA_COMMENT_START_BLOCK, out, LUA_COMMENT_END_BLOCK)

	return out

# --- ADD/REMOVE LINE LOGIC --- #

def remove_generated_code(file_lines):

	out = []
	ignore = False
	for idx, line in enumerate(file_lines):
		if ignore:
			print('  Remove line %d :: %s' % (idx + 1, line))
			if line.endswith(LUA_COMMENT_END_BLOCK):
				ignore = False
			continue

		if line.endswith((LUA_COMMENT_LINE, LUA_COMMENT_START_BLOCK)):
			print('  Remove line %d :: %s' % (idx + 1, line))
			if line.endswith(LUA_COMMENT_START_BLOCK):
				ignore = True
			continue

		if line.endswith(LUA_COMMENT_ORIGINAL):
			print('  Restore line %d :: %s' % (idx + 1, line))
			line = generate_uncomment_lua_code(line)

		out.append(line)

	# Replace lines
	del file_lines[:]
	file_lines.extend(out)

def add_generated_code(definition_dict, file_lines):

	helper_code = ''
	start_checks = []
	stop_checks = []
	local_checks = []
	event_func_checks = []
	target_seconds_dict = {}
	premonition_seconds_dict = {}
	event_dict = {}
	replace_line_dict = {}

	if 'premonition' in definition_dict:
		for timer_id, prop_dict in definition_dict['premonition'].items():

			channel = prop_dict.get('channel', DEFAULT_PREMONITION_CHAT_CHANNEL)
			message = prop_dict.get('fullMessage')
			if not message:
				label = prop_dict.get('alias', timer_id)
				desc = prop_dict.get('message', DEFAULT_PREMONITION_CHAT_MESSAGE)
				message = '[%s] %s' % (label, desc)

			helper_code += generate_premonition_yell_lua_code(timer_id, message, channel)
			start_checks.append('%s:Start(' % timer_id)
			stop_checks.append('%s:Stop(' % timer_id)
			local_checks.append('local %s' % timer_id)
			premonition_seconds_dict[timer_id] = prop_dict.get('seconds', DEFAULT_PREMONITION_SECONDS)

	# Scan file for key information
	is_register_combat_event_block = False
	for idx, line in enumerate(file_lines):

		if is_register_combat_event_block:
			if line .startswith(')'):
				is_register_combat_event_block = False
			else:
				event_id, spell_ids = parse_combat_event_register_lua_code(line)
				if event_id:
					event_dict[event_id] = {
						'line': line,
						'spell_ids': spell_ids
					}
			continue

		if 'mod:RegisterEventsInCombat(' in line:
			is_register_combat_event_block = True
			continue

		# Optimization
		if 'function mod:OnCombatStart(' in line:
			break

		if not any(local_check in line for local_check in local_checks):
			continue

		matches = re.match(r'local (\w+)[^=]*= mod:[^\(]+\((\d+(\.\d+)?),', line)
		if not matches:
			print('  Error processing line %d :: %s' % (idx + 1, line))
			continue

		timer_id = matches.group(1)
		target_seconds = matches.group(2)
		target_seconds_dict[timer_id] = target_seconds

	# Check registered combat events
	if 'event' in definition_dict:

		# Generate more helper code
		helper_code += generate_event_chat_table_block_lua_code(definition_dict['event'])

		for event_id, event_definition_dict in definition_dict['event'].items():

			event_func_checks.append('function mod:%s(' % event_id)

			# TODO Handle case if event ID is not defined
			event_info_dict = event_dict[event_id]
			additional_spell_ids = event_definition_dict.keys() - event_info_dict['spell_ids']
			if additional_spell_ids:
				print('  Detected new spell %s IDs %s' % (event_id, additional_spell_ids))
				replace_line_dict[event_info_dict['line']] = '\t"%s %s",%s' % (event_id, ' '.join(event_info_dict['spell_ids'] | additional_spell_ids), LUA_COMMENT_LINE)

	event_func_checks = tuple(event_func_checks)

	# Finalize helper code
	helper_code = '%s\n%s\n%s' % (LUA_COMMENT_START_BLOCK, helper_code, LUA_COMMENT_END_BLOCK)

	# Inject code
	for idx, line in zip(range(len(file_lines)-1, -1, -1), reversed(file_lines)):

		if 'function mod:OnCombatStart(' in line:

			print('  Add helper code at line %d (%d lines)' % (idx + 1, len(helper_code.splitlines())))
			file_lines.insert(idx, helper_code)

		elif any(start_check in line for start_check in start_checks):

			matches = re.match(r'([ \t]*)([^:]+):Start\(([^)]*)\)', line)
			if not matches:
				print('  Error processing line %d :: %s' % (idx + 1, line))
				continue

			indent = matches.group(1)
			timer_id = matches.group(2)
			target_seconds = matches.group(3) or target_seconds_dict[timer_id]
			premonition_seconds = premonition_seconds_dict[timer_id]

			new_line = generate_set_premonition_yell_lua_code(indent, timer_id, target_seconds, premonition_seconds)
			print('  Add line %d :: %s' % (idx + 1, new_line))
			file_lines.insert(idx + 1, new_line)

		elif any(stop_check in line for stop_check in stop_checks):

			matches = re.match(r'([ \t]*)([^:]+):Stop\(', line)

			if not matches:
				print('  Error processing line %d :: %s' % (idx + 1, line))
				continue

			indent = matches.group(1)
			timer_id = matches.group(2)

			new_line = generate_unset_premonition_yell_lua_code(indent, timer_id)
			print('  Add line %d :: %s' % (idx + 1, new_line))
			file_lines.insert(idx + 1, new_line)

		elif line.startswith(event_func_checks):

			event_id = parse_event_function_lua_code(line)

			if not event_id:
				print('  Error processing line %d :: %s' % (idx + 1, line))
				continue

			new_line = generate_event_block_lua_code(event_id)
			file_lines.insert(idx + 1, new_line)
			print('  Add %s event code at line %d (%d lines)' % (event_id, idx + 1, len(helper_code.splitlines())))

		elif line in replace_line_dict:

			replace_line = replace_line_dict[line]
			del replace_line_dict[line]
			file_lines[idx] = generate_comment_lua_code(line)
			print('  Comment line %d :: %s' % (idx + 1, line))
			file_lines.insert(idx, replace_line)
			print('  Add line %d :: %s' % (idx + 2, replace_line))



# --- MAIN --- #

exitCode = main(sys.argv)
exitCode and sys.exit(exitCode)
print('Done!')

if not 'PROMPT' in os.environ:
	input()