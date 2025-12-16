# omni-glot
#### A polyglot which is a HTML, Python, JAR, PDF, JPEG and PDF file simulataneously

## How does it work ?
Many parsers and file viewers are very lenient with how they process the information stored in a file. For omniglot we take advantage of the following parser quirks

* Python: The python interpreter has the ability to execute ZIP files (originally introduced so python packages can be distributed as ZIP files). It does so by scanning for the ZIP EOCD and it scans from the end of the file. Once the EOCD is found, it jumps to the Local Header, looking for the entrypoint ```__main__.py``` file which it executes.

* Java JAR: A JAR is literally a ZIP file with some metadata in the ```META-INF/MANIFEST.MF``` file. However Java is stricter than Python and there can be no junk after the EOCD, otherwise Java treats it as a corrupted file. We trick Java by using the ZIP Comment Field. The ZIP standard allows for a variable length comment at the very end of the file, where we can put our PDF footer, which the Java treats as harmless

* JPEG: JPEG parsers are stream based. They expect the file to start with the magic bytes ```FF D8``` (Start of Image), but they are designed to skip over metadata chunks they dont understand. The Omni-glot is physically a JPEG at the very beginning (Offset 0). We hide the headers for the other formats (HTML, PDF) inside a JPEG Comment Segment indicated by the magic bytes ```FF FE```.

* HTML: Web browsers are extremely forgiving and can render HTML with a lot of junk data as long as they can find valid HTML tags. We inject HTML comment markers in the JPEG header field to hide the binary image data, and CSS to hide binary header data which remains

* PDF: PDF files require a ```%PDF-``` header near the start and a ```%%EOF``` marker at the very end. However, it allows for "stream objects" which are nothing but containers meant to hold fonts or images. We place the ```%PDF-1.4``` signature inside the JPEG comment block so it exists near the top but doesnt break the image) and wrap the payload inside a PDF stream object

* MP3:  Stream based media players (like VLC) do not require a file header at the beginning. They scan the entire file looking for Sync Bytes ```FF FB``` that indicate the start of an audio frame. We inject the audio data into the middle of the file (inside the PDF stream object). The media player ignores the JPEG and PDF headers, finds the audio sync bytes, and starts playing the music stream.

## Practical Applications

Polyglots can be easily abused to stealthily drop malware, as they have a very low detection rate and will not even be suspected by the human users.

## File structure


