dos2unix $1
gawk 'BEGIN { RS="\n\n"; FS="\n"; OFS=" "; } /./ { for (i=1; i <=NF; i++) { printf "%s ", $i; } printf "\n\n"; }' $1 |sed -e 's/ $//' |iconv -f UTF-8 -t US-ASCII//TRANSLIT |sed -e 's/ \. \. \./.../g' >processed/${1##*/}
