import os
import struct
import io
import zipfile
from PIL import Image

class OmniPolyglotGenerator:
    def __init__(self):
        #bytecode for the jvm
        with open("java_bytecode.txt" , "r") as f:
            self.java_class_hex = f.read()

    def _create_zip_payload(self, python_code):
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, 'w', zipfile.ZIP_STORED) as zf:
            manifest = "Manifest-Version: 1.0\r\nMain-Class: Polyglot\r\n\r\n"
            zf.writestr('META-INF/MANIFEST.MF', manifest)
            zf.writestr('Polyglot.class', bytes.fromhex(self.java_class_hex))
            zf.writestr('__main__.py', python_code)
        return bio.getvalue()

    def _fix_zip_offsets(self, zip_data, offset_shift, comment_length=0):

        eocd_idx = zip_data.rfind(b'PK\x05\x06')
        if eocd_idx == -1: 
            return zip_data

        zip_mutable = bytearray(zip_data)
        
        eocd_off = eocd_idx + 16
        old_cd_off = struct.unpack('<I', zip_mutable[eocd_off:eocd_off+4])[0]
        struct.pack_into('<I', zip_mutable, eocd_off, old_cd_off + offset_shift)
        
        struct.pack_into('<H', zip_mutable, eocd_idx + 20, comment_length)

        #weird cd patching
        curr = old_cd_off
        while curr < eocd_idx:
            if zip_mutable[curr:curr+4] != b'PK\x01\x02': 
                break
            
            local_off_idx = curr + 42
            old_local = struct.unpack('<I', zip_mutable[local_off_idx:local_off_idx+4])[0]
            struct.pack_into('<I', zip_mutable, local_off_idx, old_local + offset_shift)
            
            n = struct.unpack('<H', zip_mutable[curr+28:curr+30])[0]
            m = struct.unpack('<H', zip_mutable[curr+30:curr+32])[0]
            k = struct.unpack('<H', zip_mutable[curr+32:curr+34])[0]
            curr += 46 + n + m + k
            
        return bytes(zip_mutable)

    def generate(self, cover_img, audio_file, output_file):
        print(f"[*] Starting Omni-Polyglot (Java Fix): {output_file}")

        try:
            img_cover = Image.open(cover_img)
            cover_io = io.BytesIO()
            img_cover.save(cover_io, format='jpeg', quality=85)
            jpeg_data = cover_io.getvalue()
        except Exception as e:
            print(f"[!] Cover Error: {e}")
            return

        if jpeg_data[:2] != b'\xff\xd8':
            print("[!] Error: Invalid JPEG.")
            return
        
        cloaking_str = b"<!-- %PDF-1.4" 
        comment_len = len(cloaking_str) + 2
        comment_block = b'\xff\xfe' + struct.pack('>H', comment_len) + cloaking_str
        stage_1_data = jpeg_data[:2] + comment_block + jpeg_data[2:]

#high z index so junk inst visible
        html_content = """
-->
<!DOCTYPE html><html><head><style>
body{margin:0;padding:0;background:#000;overflow:hidden}
#cloak{position:fixed;top:0;left:0;width:100%;height:100%;background:#ffffff;z-index:99999;
display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:24px;color:#333}
</style></head><body><div id="cloak">I AM AN HTML FILE TOO</div></body></html>
"""
        html_bytes = html_content.encode('utf-8')

        start_offset = len(stage_1_data) + len(html_bytes)
        
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
        
        text = b"BT /F1 24 Tf 100 700 Td (I AM A PDF FILE TOO) Tj ET"
        obj4 = f"4 0 obj\n<< /Length {len(text)} >>\nstream\n".encode('utf-8') + text + b"\nendstream\nendobj\n"
        
        static_pdf_body = obj1 + obj2 + obj3 + obj4

        python_code = "print('I AM A PYTHON SCRIPT TOO')"
        zip_raw = self._create_zip_payload(python_code)
        
        audio_bytes = b''
        if audio_file and os.path.exists(audio_file):
            with open(audio_file, 'rb') as f: 
                audio_bytes = f.read()


        
        pdf_footer_start = b"\nendstream\nendobj\n"
        

        #xref offsets for footer string
        payload_len = len(audio_bytes) + len(zip_raw)
        obj5_header = f"5 0 obj\n<< /Length {payload_len} >>\nstream\n".encode('utf-8')
        
        obj5_start = start_offset + len(static_pdf_body)
        
        off1 = start_offset
        off2 = off1 + len(obj1)
        off3 = off2 + len(obj2)
        off4 = off3 + len(obj3)
        off5 = off4 + len(obj4)
        
        xref = b"xref\n0 6\n0000000000 65535 f \n"
        xref += f"{off1:010} 00000 n \n".encode('utf-8')
        xref += f"{off2:010} 00000 n \n".encode('utf-8')
        xref += f"{off3:010} 00000 n \n".encode('utf-8')
        xref += f"{off4:010} 00000 n \n".encode('utf-8')
        xref += f"{off5:010} 00000 n \n".encode('utf-8') 
        
        trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{off5 + len(obj5_header) + payload_len + len(pdf_footer_start)}\n%%EOF\n".encode('utf-8')
        
        #full suffix after zip eocd
        full_suffix = pdf_footer_start + xref + trailer
        
        #java scan limit check
        if len(full_suffix) > 65535:
            print("[!] PDF Footer too large for Zip Comment. Jar will fail.")
            return

        print(f"[*] Masking PDF end ({len(full_suffix)} bytes) as Zip Comment...")
        
        zip_injection_offset = obj5_start + len(obj5_header) + len(audio_bytes)
        
        fixed_zip = self._fix_zip_offsets(zip_raw, zip_injection_offset, comment_length=len(full_suffix))

        final_data = stage_1_data + html_bytes + static_pdf_body + obj5_header + audio_bytes + fixed_zip + full_suffix
        
        with open(output_file, 'wb') as f:
            f.write(final_data)
            
        print(f"[*] SUCCESS: {output_file}")

if __name__ == "__main__":

    gen = OmniPolyglotGenerator()
    gen.generate("cover.jpg", "song.mp3", "omni_artifact.jpg")