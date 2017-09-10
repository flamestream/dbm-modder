import sys
import json
import re
import os
import pathlib

SHORT_DESCRIPTION = 'Modifies DBM script to add custom yell notifier.'
LUA_COMMENT_LINE        = '-- FS-GENERATED'
LUA_COMMENT_START_BLOCK = '-- FS-GENERATED-START'
LUA_COMMENT_END_BLOCK   = '-- FS-GENERATED-END'
DEFAULT_CONFIG_FILE = 'config.json'
DEFAULT_WOW_ADDON_DIR = str(os.path.normpath(os.path.join(pathlib.Path.home(), '..', 'Public', 'Games', 'World of Warcraft', 'Interface', 'Addons')))
DEFAULT_CHAT_CHANNEL = 'YELL'
DEFAULT_PREEMPT_SECONDS = 5
DEFAULT_CHAT_MESSAGE = r'%.0f seconds'

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

def generate_preemptive_yell_lua_code(timer_id, message, channel):

	return """
local function fs_yell_%s(preemptTime)
	SendChatMessage(string.format("%s", preemptTime), "%s")
end
local function fs_set_%s(self, targetTime, preemptTime)
	self:Schedule(targetTime-preemptTime, fs_yell_%s, preemptTime)
end
local function fs_unset_%s(self)
	self:Unschedule(fs_yell_%s)
end
""" % (timer_id, message, channel, timer_id, timer_id, timer_id, timer_id)

def generate_set_preemptive_yell_lua_code(indent, timer_id, target_seconds, preempt_seconds):

	return '%sfs_set_%s(self, %s, %s) %s' % (indent, timer_id, target_seconds, preempt_seconds, LUA_COMMENT_LINE)

def generate_unset_preemptive_yell_lua_code(indent, timer_id):

	return '%sfs_unset_%s(self) %s' % (indent, timer_id, LUA_COMMENT_LINE)

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

		out.append(line)

	# Replace lines
	del file_lines[:]
	file_lines.extend(out)

def add_generated_code(definition_dict, file_lines):

	helper_code = ''
	start_checks = []
	stop_checks = []
	local_checks = []
	target_seconds_dict = {}
	preempt_seconds_dict = {}

	for timer_id, prop_dict in definition_dict.items():

		channel = prop_dict.get('channel', DEFAULT_CHAT_CHANNEL)
		message = prop_dict.get('fullMessage')
		if not message:
			message = '[%s] %s' % (prop_dict.get('alias', timer_id), prop_dict.get('message', DEFAULT_CHAT_MESSAGE))

		helper_code += generate_preemptive_yell_lua_code(timer_id, message, channel)
		start_checks.append('%s:Start(' % timer_id)
		stop_checks.append('%s:Stop(' % timer_id)
		local_checks.append('local %s' % timer_id)
		preempt_seconds_dict[timer_id] = prop_dict.get('preemptSeconds', DEFAULT_PREEMPT_SECONDS)

	helper_code = '%s\n%s\n%s' % (LUA_COMMENT_START_BLOCK, helper_code, LUA_COMMENT_END_BLOCK)

	# Scan file for key information
	for idx, line in enumerate(file_lines):

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
			preempt_seconds = preempt_seconds_dict[timer_id]

			new_line = generate_set_preemptive_yell_lua_code(indent, timer_id, target_seconds, preempt_seconds)
			print('  Add line %d :: %s' % (idx + 1, new_line))
			file_lines.insert(idx + 1, new_line)

		elif any(stop_check in line for stop_check in stop_checks):

			matches = re.match(r'([ \t]*)([^:]+):Stop\(', line)

			if not matches:
				print('  Error processing line %d :: %s' % (idx + 1, line))
				continue

			indent = matches.group(1)
			timer_id = matches.group(2)

			new_line = generate_unset_preemptive_yell_lua_code(indent, timer_id)
			print('  Add line %d :: %s' % (idx + 1, new_line))
			file_lines.insert(idx + 1, new_line)

# --- MAIN --- #

exitCode = main(sys.argv)
exitCode and sys.exit(exitCode)
print('Done!')

if not 'PROMPT' in os.environ:
	input()