#!/bin/bash
# Исправляет DPI метаданные у всех файлов вида 1.png, 2.png... в папке input/

cd "$(dirname "$0")/input" || exit

for file in [0-9]*.jpg; do
    if [ -f "$file" ]; then
        echo "Правим DPI для файла: $file"
        mogrify -units PixelsPerInch -density 600 "$file"
    fi
done

echo "✅ Все файлы обновлены до 600 DPI!"
