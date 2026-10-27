"""Prepare distinct editable font faces from the OSS pilot's EOT output.
Only embedded copies receive explicit family names. Source OTFs stay unchanged.
"""
import struct

def checksum(b):
    b+=b'\0'*(-len(b)%4)
    return sum(struct.unpack('>'+str(len(b)//4)+'I',b))&0xffffffff

def font_copy(b,family):
    size=struct.unpack_from('<I',b,4)[0];start=len(b)-size;sfnt=b[start:]
    count=struct.unpack_from('>H',sfnt,4)[0];tables={}
    for i in range(count):
        tag,_,off,n=struct.unpack_from('>4sIII',sfnt,12+i*16);tables[tag]=bytearray(sfnt[off:off+n])
    old=tables[b'name'];_,n,off=struct.unpack_from('>HHH',old);records=[]
    targets={1,2,3,4,6,16,17}
    for i in range(n):
        p,e,l,k,length,loc=struct.unpack_from('>HHHHHH',old,6+i*12)
        if k not in targets:records.append((p,e,l,k,bytes(old[off+loc:off+loc+length])))
    names={1:family,2:'Regular',3:family+' HTML Export',4:family,6:family.replace(' ','-'),16:family,17:'Regular'}
    records += [(3,1,1033,k,v.encode('utf-16-be')) for k,v in names.items()]
    records.sort(key=lambda x:x[:4]);data=bytearray();entries=bytearray()
    for p,e,l,k,s in records:
        entries+=struct.pack('>HHHHHH',p,e,l,k,len(s),len(data));data+=s
    tables[b'name']=bytearray(struct.pack('>HHH',0,len(records),6+len(entries))+entries+data)
    if b'OS/2' in tables:
        struct.pack_into('>H',tables[b'OS/2'],4,400)
        if len(tables[b'OS/2'])>=64:struct.pack_into('>H',tables[b'OS/2'],62,64)
    if b'head' in tables:
        struct.pack_into('>I',tables[b'head'],8,0)
        struct.pack_into('>H',tables[b'head'],44,0)
    tags=sorted(tables);header=bytearray(sfnt[:12]);payload=bytearray();directory=bytearray();offset=12+len(tags)*16;head_offset=None
    for tag in tags:
        table=tables[tag];directory+=struct.pack('>4sIII',tag,checksum(bytes(table)),offset,len(table))
        if tag==b'head':head_offset=offset
        payload+=table;payload+=b'\0'*(-len(table)%4);offset=12+len(tags)*16+len(payload)
    result=header+directory+payload
    if head_offset is not None:struct.pack_into('>I',result,head_offset+8,(0xb1b0afba-checksum(bytes(result)))&0xffffffff)
    # EOT names are UTF-16LE, unlike the original library's UTF-16BE strings.
    old_offset=82;strings=[]
    for _ in range(4):
        n=struct.unpack_from('<H',b,old_offset)[0];old_offset+=2
        strings.append(b[old_offset:old_offset+n].decode('utf-16-be'));old_offset+=n+2
    strings=[family,'Regular',strings[2],family]
    assert checksum(bytes(result))==0xb1b0afba
    eot=bytearray(b[:82]);struct.pack_into('<I',eot,28,400)
    if head_offset is not None:struct.pack_into('<I',eot,60,struct.unpack_from('>I',result,head_offset+8)[0])
    for s in strings:
        enc=s.encode('utf-16-le');eot+=struct.pack('<H',len(enc))+enc+b'\0\0'
    eot+=b[old_offset:start];eot+=result
    struct.pack_into('<II',eot,0,len(eot),len(result))
    return bytes(eot)

