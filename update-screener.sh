SOURCE="$HOME/Downloads/idx-screener-stock-logos-changes"
DEST="/Users/topremitdevice/Desktop/WA/oliver-kell-screener"

if [ -d "$SOURCE" ] && [ -d "$DEST" ]; then
    rsync -av "$SOURCE/" "$DEST/"
    echo "✅ Project updated successfully!"
else
    echo "❌ Source or project folder not found."
fi