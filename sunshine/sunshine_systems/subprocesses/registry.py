SUBPROCESS_REGISTRY = [
    {
        'name': 'ControlPanel',
        'folder': 'control_panel',
        'critical': True,
        'show_console': True,  # Always show console for control panel in dev
    },
    {
        'name': 'SunBoxInterface',
        'folder': 'sunbox_interface',
        'critical': True,
        'show_console': True,
    },
    # Add additional subprocesses here as needed
    # To create a new subprocess:
    # 1. Copy the template_subprocess folder
    # 2. Rename it to your desired name
    # 3. Edit the main.py to set the process name
    # 4. Add entry here with folder name
    # {
    #     'name': 'MyNewProcess',
    #     'folder': 'my_new_process',
    #     'critical': False,
    #     'show_console': False,
    # },
]

def get_subprocess_folder_by_name(name):
    """Get subprocess folder by name from registry."""
    for config in SUBPROCESS_REGISTRY:
        if config['name'] == name:
            return config['folder']
    return None

# Debug: Print registry on import
print(f"DEBUG: Loaded {len(SUBPROCESS_REGISTRY)} processes from registry:")
for proc in SUBPROCESS_REGISTRY:
    print(f"  - {proc['name']} ({proc['folder']})")
