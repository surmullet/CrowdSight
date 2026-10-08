"""Build a portable, prediction-blind human review page from locked samples."""
import argparse
import base64
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--intake', required=True, type=Path)
    parser.add_argument('--layouts', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    import cv2
    import numpy as np
    layouts = json.loads(args.layouts.read_bytes())
    rows = []
    for source, spec in layouts['videos'].items():
        selection = json.loads((args.intake/source/'frames.json').read_bytes())
        for record in selection['frames']:
            raw = (args.intake/source/record['path']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != record['sha256']:
                raise ValueError('Frame hash mismatch')
            frame = cv2.resize(cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR), tuple(layouts['reference_size']))
            for space in spec['spaces']:
                x0,y0,x1,y1 = space['box']
                context = frame.copy()
                cv2.rectangle(context, (x0,y0), (x1,y1), (0,255,255), 3)
                images = []
                for image in (frame[y0:y1,x0:x1], context):
                    ok, encoded = cv2.imencode('.jpg', image)
                    if not ok:
                        raise ValueError('Image encode failed')
                    images.append(base64.b64encode(encoded).decode())
                rows.append(dict(source=source, frame_index=record['frame_index'], space_id=space['id'],
                                 media_time_s=record['media_time_s'], source_sha256=selection['source_sha256'],
                                 frame_sha256=record['sha256'], crop=images[0], context=images[1], state=None))
    payload = json.dumps(dict(layouts_sha256=hashlib.sha256(args.layouts.read_bytes()).hexdigest(), rows=rows))
    page = '''<!doctype html><meta charset="utf-8"><title>Parking human review</title>
<style>body{font:18px system-ui;max-width:1100px;margin:24px auto}button,input{font:inherit;margin:5px;padding:8px}#context{width:100%}#crop{height:150px}#status{white-space:pre-wrap}</style>
<h1>Prediction-blind parking review</h1><p>Judge the highlighted stall: occupied, available, or unknown (blocked, ambiguous geometry, unsupported vehicle, or corrupt image). No model predictions or provisional labels are shown.</p>
<label>Reviewer name <input id="reviewer"></label><p id="status"></p><img id="crop"><img id="context">
<div><button onclick="mark('O')">Occupied</button><button onclick="mark('A')">Available</button><button onclick="mark('U')">Unknown</button></div>
<button onclick="step(-1)">Previous</button><button onclick="step(1)">Next</button><button onclick="save()">Export review JSON</button>
<label>Resume exported review <input type="file" id="resume" accept=".json"></label>
<script>const data=PAYLOAD;let i=0;const $=id=>document.getElementById(id);
function show(){const r=data.rows[i];$('status').textContent=`${i+1}/${data.rows.length}: ${r.source} frame ${r.frame_index} stall ${r.space_id}\nChoice: ${r.state||'unreviewed'}; completed ${data.rows.filter(x=>x.state).length}`;for(const key of ['crop','context'])$(key).src='data:image/jpeg;base64,'+r[key];}
function step(n){i=Math.max(0,Math.min(data.rows.length-1,i+n));show();}function mark(v){data.rows[i].state=v;step(1);}
function save(){if(!$('reviewer').value.trim()){alert('Enter your reviewer name.');return;}const result={schema_version:1,reviewer_id:$('reviewer').value.trim(),reviewed_at:new Date().toISOString(),layouts_sha256:data.layouts_sha256,human_review_completed:data.rows.every(x=>x.state),status:data.rows.every(x=>x.state)?'HUMAN_REVIEW_SUBMITTED':'HUMAN_REVIEW_PARTIAL',rows:data.rows.map(({crop,context,...r})=>r)};const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='parking-human-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('resume').onchange=async e=>{try{const r=JSON.parse(await e.target.files[0].text());if(r.layouts_sha256!==data.layouts_sha256||r.rows.length!==data.rows.length)throw Error('Different review pack');for(let n=0;n<data.rows.length;n++){const a=data.rows[n],b=r.rows[n];for(const k of ['source','space_id','frame_index','frame_sha256','source_sha256'])if(a[k]!==b[k])throw Error('Row identity mismatch');if(![null,'O','A','U'].includes(b.state))throw Error('Invalid state');}r.rows.forEach((r,n)=>data.rows[n].state=r.state);$('reviewer').value=r.reviewer_id;show();}catch(err){alert(err.message);}};show();</script>'''
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(page.replace('PAYLOAD', payload.replace('<', '\\u003c')))
    print(f'Created {args.output}: {len(rows)} prediction-blind review decisions')


if __name__ == '__main__':
    main()
