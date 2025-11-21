export KICAD_ALLOC_CONSOLE=1   # If you are on Windows, this variable is required to show any output
export KICAD_ENABLE_WXTRACE=1  # This enables KiCad's tracing system even when running a release build
export WXTRACE=KICAD_API       # This enables trace output for the API subsystem
echo "EnableAPILogging=1" > ~/Library/Preferences/kicad/9.0/kicad_advanced
open -a KiCad
