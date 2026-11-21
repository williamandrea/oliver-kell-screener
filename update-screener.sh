SOURCE="$HOME/Downloads/idx-screener-four-scans-fixes"
DEST="/Users/topremitdevice/Desktop/WA/oliver-kell-screener"

if [ -d "$SOURCE" ] && [ -d "$DEST" ]; then
    rsync -av "$SOURCE/" "$DEST/"
    echo "✅ Project updated successfully!"
else
    echo "❌ Source or project folder not found."
fi