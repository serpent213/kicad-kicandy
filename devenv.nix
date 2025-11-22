{ pkgs, ... }:
{
  # https://devenv.sh/basics/
  # Help the Python language server
  env.PYTHONPATH = "./.devenv/state/venv/lib/python3.13/site-packages";

  # https://devenv.sh/packages/
  packages =
    with pkgs;
    [
      python313Packages.fonttools
    ];

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
    set -e
    PLUGIN_FOLDER=~/Documents/kicad/9.0/plugins/kicad-kicandy
    mkdir -p $PLUGIN_FOLDER/icons
    cp -rv plugin.json requirements.txt *.py ui $PLUGIN_FOLDER
    cp -rv icons/*.png $PLUGIN_FOLDER/icons
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
    # Avoid having Python files in pwd
    cd ~

    /Applications/KiCad/KiCad.app/Contents/MacOS/kicad
  '';

  # See full reference at https://devenv.sh/reference/options/
}
