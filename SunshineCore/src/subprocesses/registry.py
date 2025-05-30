SUBPROCESS_REGISTRY = [
    {
        'name': 'ControlPanel',
        'folder': 'control_panel',
        'critical': True,
        'show_console': True,
    },
]

def get_subprocess_folder_by_name(name):
    """Get subprocess folder by name from registry."""
    for config in SUBPROCESS_REGISTRY:
        if config['name'] == name:
            return config['folder']
    return None
