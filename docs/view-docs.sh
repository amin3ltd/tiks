#!/bin/bash

# tiks Documentation Viewer
# This script opens the tiks user guide in your default browser

echo "Opening tiks User Guide..."

# Check if we're in the docs directory
if [ ! -f "index.html" ]; then
    echo "Error: Please run this script from the docs directory"
    echo "Usage: cd docs && ./view-docs.sh"
    exit 1
fi

# Try different methods to open the browser
if command -v xdg-open >/dev/null 2>&1; then
    # Linux
    xdg-open index.html
elif command -v open >/dev/null 2>&1; then
    # macOS
    open index.html
elif command -v start >/dev/null 2>&1; then
    # Windows
    start index.html
else
    echo "Could not automatically open browser."
    echo "Please manually open index.html in your web browser."
    echo "For best results, serve the files with a local web server:"
    echo "  python3 -m http.server 8080"
    echo "  Then open: http://localhost:8080"
fi

echo "tiks User Guide opened successfully!"
echo ""
echo "Navigation:"
echo "• Use the top navigation bar to jump between sections"
echo "• Click on role cards to navigate to specific roles"
echo "• Scroll smoothly through the documentation"
echo ""
echo "Keyboard shortcuts:"
echo "• Home/End: Jump to top/bottom of page"
echo "• Ctrl+/: Show keyboard shortcuts help"