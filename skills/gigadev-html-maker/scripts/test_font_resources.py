#!/usr/bin/env python3
"""Focused no-substitution, weight, provenance and binary metadata tests."""
import pathlib, struct, tempfile, unittest
from font_resources import read_sfnt, resolve


def font(weight, italic, origin, family='SB Serif Display', full=None, ps='ExamplePS', typographic=None):
    names={'1':[family], '4':[full or family], '6':[ps]}
    if typographic: names['16']=[typographic]
    return {'names':names,'weight':weight,'italic':italic,'path':'/'+origin+'/'+ps,'postscriptName':ps,'sha256':origin+ps,'origin':origin}

class FontResources(unittest.TestCase):
    def test_name_os2_offsets_and_bounds(self):
        strings=[(1,'Sample Family'),(2,'Regular'),(4,'Sample Family'),(6,'SamplePS')]
        payload=b''; records=[]
        for ident,text in strings:
            encoded=text.encode('utf-16be');records.append(struct.pack('>HHHHHH',3,1,0x409,ident,len(encoded),len(payload)));payload+=encoded
        name=struct.pack('>HHH',0,len(records),6+12*len(records))+b''.join(records)+payload
        os2=bytearray(64);struct.pack_into('>H',os2,4,600);struct.pack_into('>H',os2,6,5);struct.pack_into('>H',os2,8,0x0200);struct.pack_into('>H',os2,62,1)
        start=12+32;data=struct.pack('>4sHHHH',b'OTTO',2,0,0,0)+struct.pack('>4sIII',b'name',0,start,len(name))+struct.pack('>4sIII',b'OS/2',0,start+len(name),len(os2))+name+os2
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'sample.otf';p.write_bytes(data);result=read_sfnt(p)
            self.assertEqual((result['weight'],result['fsType'],result['italic'],result['postscriptName']),(600,0x200,True,'SamplePS'))
            p.write_bytes(data[:-5]);self.assertRaises(ValueError,read_sfnt,p)
    def test_origin_preference_and_no_substitution(self):
        local=font(400,False,'local');embedded=font(400,False,'embedded')
        req={'family':'SB Serif Display','bold':False,'italic':False}
        self.assertEqual(resolve(req,[local,embedded])['status'],'ambiguous-exact-faces')
        self.assertEqual(resolve(req,[local,embedded],'local')['origin'],'local')
        self.assertEqual(resolve(req,[local,embedded],'embedded')['origin'],'embedded')
        self.assertEqual(resolve({'family':'TT Firs','bold':False,'italic':False},[local])['status'],'external-or-unresolved')
        self.assertEqual(resolve({'family':'SB-Serif Display','bold':False,'italic':False},[local])['status'],'external-or-unresolved')
        self.assertEqual(resolve({'family':'SB Serif Display','bold':None,'italic':False},[local])['status'],'external-or-unresolved')
        mismatch=font(400,False,'embedded',family='Roboto');mismatch['declaredIdentityStatus']='mismatch'
        self.assertEqual(resolve({'family':'Roboto','bold':False,'italic':False},[mismatch])['status'],'external-or-unresolved')
    def test_named_face_weight(self):
        light=font(300,False,'local',family='SB Sans Display Light',full='SB Sans Display Light',typographic='SB Sans Display')
        result=resolve({'family':'SB Sans Display Light','bold':False,'italic':False},[light])
        self.assertEqual((result['status'],result['weight']),('exact-face-candidate',300))
        self.assertEqual(resolve({'family':'SB Sans Display Light','bold':True,'italic':False},[light])['status'],'external-or-unresolved')
        self.assertEqual(resolve({'family':'SB Sans Display','bold':False,'italic':False},[light])['status'],'external-or-unresolved')
if __name__=='__main__':unittest.main()
