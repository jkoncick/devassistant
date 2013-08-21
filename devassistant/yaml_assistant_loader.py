import os

from devassistant import argument
from devassistant import exceptions
from devassistant.logger import logger
from devassistant import yaml_loader
from devassistant import yaml_snippet_loader
from devassistant import settings
from devassistant.assistants import yaml_assistant

class YamlAssistantLoader(object):
    assistants_dirs = list(map(lambda x: os.path.join(x, 'assistants'), settings.DATA_DIRECTORIES))
    # mapping of assistant roles to lists of top-level assistant instances
    _assistants = {}

    @classmethod
    def get_top_level_assistants(cls, roles=settings.ASSISTANT_ROLES):
        """Returns list of top level assistants with specified roles (defaults to all roles).

        Args:
            roles: list of names of roles, defaults to all roles
        Returns:
            list of YamlAssistant instances with specified roles
        """
        cls.load_all_assistants(roles=roles)
        result = []
        for r in roles:
            result.extend(cls._assistants[r])

        return result

    @classmethod
    def load_all_assistants(cls, roles):
        """Fills self._assistants with loaded YamlAssistant instances of requested roles

        Args:
            roles: list of required assistant roles
        """
        to_load = set(roles) - set(cls._assistants.keys())
        for tl in to_load:
            dirs = [os.path.join(d, tl) for d in cls.assistants_dirs]
            file_hierarchy = cls.get_assistants_file_hierarchy(dirs)
            cls._assistants[tl] = cls.get_assistants_from_file_hierarchy(file_hierarchy)

    @classmethod
    def get_assistants_from_file_hierarchy(cls, file_hierarchy):
        """Accepts file_hierarch as returned by cls.get_assistant_file_hierarchy and returns
        instances of YamlAssistant for loaded files

        Args:
            file_hierarchy: structure as described in cls.get_assistants_file_hierarchy
        Returns:
            list of top level assistants from given hierarchy; these assistants contain
            references to instances of their subassistants (and their subassistants, ...)
        """
        result = []

        for name, subhierarchy in file_hierarchy.items():
            loaded_yaml = yaml_loader.YamlLoader.load_yaml_by_path(subhierarchy[0])
            ass = cls.assistant_from_yaml(subhierarchy[0], loaded_yaml)
            ass._subassistants = cls.get_assistants_from_file_hierarchy(subhierarchy[1])
            result.append(ass)

        return result

    @classmethod
    def get_assistants_file_hierarchy(cls, dirs):
        """Returns assistants file hierarchy structure (see below) representing assistant
        hierarchy in given directories.

        It works like this:
        1. It goes through all *.yaml files in all given directories and adds them into
           hierarchy (if there are two files with same name in more directories, the file
           from first directory wins).
        2. For each {name}.yaml file, it calls itself recursively for {name} subdirectories
           of all given directories.

        Args:
            dirs: directories to search
        Returns:
            hierarchy structure that looks like this:
            {'assistant1':
                ('/path/to/assistant1.yaml', {<hierarchy of subassistants>}),
             'assistant2':
                ('/path/to/assistant2.yaml', {<another hieararchy of subassistants})
            }
        """
        result = {}
        for d in filter(lambda d: os.path.exists(d), dirs):
            for f in filter(lambda f: f.endswith('.yaml'), os.listdir(d)):
                assistant_name = f[:-5]
                if assistant_name not in result:
                    subas_dirs = [os.path.join(dr, assistant_name) for dr in dirs]
                    result[assistant_name] = (os.path.join(d, f),
                                              cls.get_assistants_file_hierarchy(subas_dirs))

        return result

    @classmethod
    def assistant_from_yaml(cls, source, y):
        """Constructs instance of YamlAssistant loaded from given structure y, loaded
        from source file source.

        Args:
            source: path to assistant source file
            y: loaded yaml structure
        Returns:
            YamlAssistant instance constructed from y with source file source
        """
        # assume only one key and value
        name, attrs = y.popitem()

        template_dir = attrs.get('template_dir', yaml_loader.YamlLoader._default_template_dir_for(source))
        assistant = yaml_assistant.YamlAssistant(name, attrs, source, template_dir)

        return assistant
