import pynvim
import logging
import xdg
import os

# pynvim uses the python logging module. The following 
# environment variables may be used to view logs:
#
# export NVIM_PYTHON_LOG_FILE=<path_to_log_file>
# export NVIM_PYTHON_LOG_LEVEL=DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# see https://pyyaml.org/wiki/PyYAMLDocumentation
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

@pynvim.plugin
class NeovimProject(object):
    _default_project_config = {
                    'config_file_version' : "1.0.0",
                    'open_browsers' : False,
                    'ack_options' : "--ignore-file=is:tags --ignore-file=ext:map --ignore-file=ext:d --ignore-file=ext:cmd",
                    'ctags' : {
                      'options': ''
                      }
                    }

    # Private methods
    def __init__(self, nvim):
        logger.info(f"start")
        self.nvim = nvim
        self._prj_root = None
        self._config = None
        self._project_session_name = xdg.Path('.prj_session')
        self._project_config_name = xdg.Path('.prj_config')
        self._config_dir = xdg.xdg_config_home().joinpath('nvim_rpy_project')
        self._config_file = self._config_dir.joinpath('config')
        self._project_list = self._config_dir.joinpath('project_list.yaml')

        try:
            # create plugin data directory is not exist
            if not os.path.isdir(self._config_dir):
                logger.info("Plugin data directory does not exits. Creating it...")
                os.makedirs(self._config_dir)
    
            # create plugin config file if not exist
            if not os.path.isfile(self._config_file):
                logger.info("Plugin config file does not exist. Creating it...")
                self._create_default_config()

        except Exception as e:
            self.nvim.out_write(f"Failed to create plugin data directory and files. Plugin will not work.")
            self.nvim.out_write(f"Set NVIM_PYTHON_LOG_FILE to view logfile.\n")
            logger.error(f"Failed to create plugin data directory/files: {e}")

        logger.info(f"end")
  

    def _create_default_config(self):
        """
        @brief This creates the plugin's config file. This config file contains 
        configurations for all projects. This config file is not the same 
        as the project config file.
        """
        self._config_file.touch()
        # create yaml file to store manifest of all projects created. This is used to provide the user
        # with a list of projects that they have created and jump to them from neovim instead of having
        # to navigate to the individual directories where the projects were created.
        self._project_list.touch()
  
    def _find_project_file(self):
        """
        @brief Search for a project file backwards from the current directory 
        all the way to the root of the file system.
        @return The path to the project file or None if not found.
        """

        d = xdg.Path(os.getcwd())
        path = None #path to the project file. This is returned by this method.
    
        while True:
            # if we found a project file, set the return value and break from the loop
            if os.path.isfile(d.joinpath(self._project_config_name)):
                path = d.joinpath(self._project_config_name)
                break
            elif d.name == '': # this mean we have reached the root of the file system.
                # note, in the if above, we already searched for the project file. 
                # It was not found. If name == '', it means the if above searched in the root of 
                # file system. We break here because we are done.
                break

            else: # otherwise, we have not yet searched up to the root of the file system.
                d = d.parent
    
        return path

    def _load_session(self):
        """
        @brief Load the previously saved session
        """
        self.nvim.command(f'silent source {self._prj_root}/{self._project_session_name}')
   
    @pynvim.command('PrjCreateCtags', sync=False)
    def prj_create_ctags(self):
        pass

    @pynvim.command('PrjNew')
    def prjnew(self):
        """
        @brief Create a new project in the current directory
        """
        if not os.path.isfile(self._project_config_name):
            try:
    
                self._prj_root = xdg.Path(os.getcwd())
    
                with open(self._project_config_name, "w") as f:
                    f.write(dump(self._default_project_config))
    
            except Exception as e:
                self._prj_root = None
                self.nvim.out_write(f"{e}\n")
        else:
            self.nvim.out_write('Project already exists in this directory. Use PrjOpen to open it.\n')

    @pynvim.command('PrjOpen')
    def prjopen(self):

        path = self._find_project_file()

        if path != None:
            self._prj_root = xdg.Path(path.parent)

            try:
                with open(self._prj_root.joinpath(self._project_config_name), 'r') as f:
                    self._config = load(f, Loader=Loader)
            except Exception as e:
                self.nvim.out_write(f"Failed to open project config file: {e}\n")

            self._load_session()

            self.nvim.out_write(f"Found project: {path}\n")

        else:
            self.nvim.out_write(f"No project found.\n")

    @pynvim.autocmd('VimLeave', pattern='*', eval='expand("<afile>")', sync=True)
    def on_vimleave(self, filename):
        if self._prj_root != None:
            self.nvim.command(f'mksession! {self._prj_root}/{self._project_session_name}')


