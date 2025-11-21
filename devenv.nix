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

  scripts.kicad-debug.exec = ''
    # If you are on Windows, this variable is required to show any output
    export KICAD_ALLOC_CONSOLE=1
    # This enables KiCad's tracing system even when running a release build
    export KICAD_ENABLE_WXTRACE=1
    # This enables trace output for the API subsystem
    export WXTRACE=KICAD_API
    # API log to ~/Documents/kicad/9.0/logs/api.log
    echo "EnableAPILogging=1" > ~/Library/Preferences/kicad/9.0/kicad_advanced

    /Applications/KiCad/KiCad.app/Contents/MacOS/kicad
  '';

  # See full reference at https://devenv.sh/reference/options/
}
