BEGIN { x = ""; count=0; }
{
    count = count + 1;
    if ($0 ~ /^Command:/) {
	x = gensub(/^Command:\s*"?(.*)"?$/, "\\1", "g");
    } else if ($0 ~ /^Sentence:/) {
	y = gensub(/^Sentence:\s*"?(.*)"?$/, "\\1", "g");
	print x, "|", y;
	x = "";
    } else if ($0 ~ /^[0-9]+\. +"?([[:alnum:]',]+ ?){2,5}!?"?\s*[:\.-][^a-zA-Z]+\w/) {
	line = gensub(/^[0-9]+\. +"?(([[:alnum:]',]+ ?){2,5})!?"?\s*[:\.-][^a-zA-Z]*/, "\\1 | ", "g");
	print line;
	x = ""
    } else if ($0 ~ /^[0-9]+\. +"?([[:alnum:]',]+ ?){2,5}\.?"?[^a-zA-Z]*$/) {
	x = gensub(/^[0-9]+\. +"?(([[:alnum:]',]+ ?){2,5})\.?"?/, "\\1", "g");
	#print x;
    } else if (length(x) > 0) {
	y = gensub(/^[^a-zA-Z]*(\w.*)"?\s*$/, "\\1", "g");
	print x, "|", y;
	#print x, "|";
	#print y;
	x = "";
    }
}
