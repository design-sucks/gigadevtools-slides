"""Source record differences must not disappear during subset mapping."""
import copy
from compare_subset_inventory import compare

b={'id':'s1-o7','kind':'text','source':{'objectId':'7'},'paragraphs':[{'text':'Link 42','level':1,'runs':[{'text':'Link','link':'https://example.test/'},{'text':' 42'}],'effectiveList':{'status':'resolved','kind':'ul'}}]}
original={'source':{'sha256':'original'},'slides':[{'sourceNumber':8,'blocks':[b]}]}
mini={'source':{'sha256':'mini'},'slides':[{'sourceNumber':1,'blocks':[copy.deepcopy(b)]}]}
mapping={'status':'pass','sourceSha256':'original','miniSha256':'mini','slides':[{'originalSlide':8,'miniSlide':1}]}
assert compare(original,mini,mapping)['status']=='pass'
for mutation in ('paragraph','link','number','marker','object'):
 other=copy.deepcopy(mini);block=other['slides'][0]['blocks'][0]
 if mutation=='paragraph':block['paragraphs']=[]
 if mutation=='link':block['paragraphs'][0]['runs'][0]['link']='https://other.test/'
 if mutation=='number':block['paragraphs'][0]['runs'][1]['text']=' 43'
 if mutation=='marker':block['paragraphs'][0]['effectiveList']['kind']='ol'
 if mutation=='object':other['slides'][0]['blocks']=[]
 assert compare(original,other,mapping)['status']=='fail',mutation
try:compare(original,mini,{**mapping,'status':'fail'})
except ValueError:pass
else:raise AssertionError('Unverified subset mapping accepted')
print('PASS subset mapping: paragraph, link, number, marker, missing object and unverified map')
