{
  # https://devenv.sh/basics/
  # Help the Python language server
  env.PYTHONPATH = ".venv/lib/python3.12/site-packages";

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };
  };

  # https://devenv.sh/scripts/
  scripts.install-plugin.exec = ''
    PLUGIN_FOLDER=~/Documents/kicad/9.0/plugins/kicad-kicandy
    mkdir -p $PLUGIN_FOLDER
    cp -rv plugin.json requirements.txt icons *.py ui $PLUGIN_FOLDER
  '';

  # See full reference at https://devenv.sh/reference/options/
}
