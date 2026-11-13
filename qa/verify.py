from pathlib import Path
import subprocess,re,json,math,hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

R=Path(__file__).resolve().parents[1]
V=R/'exports'/'假如时间可以买卖.mp4'
F='/Users/USER/.local/bin/ffmpeg'
Q=R/'qa'; (Q/'decoded').mkdir(exist_ok=True)
# Every third of a second, plus every frame around the three pivotal transitions.
selected=sorted(set(range(0,900,10))|set(range(318,349))|set(range(349,370))|set(range(699,711))|{899})
full=[0,45,140,210,290,330,360,410,530,615,707,780,870,899]
count=0; luminance=[]; kept=[]
with (Q/'full-decode.log').open('w') as log:
    p=subprocess.Popen([F,'-hide_banner','-i',str(V),'-map','0:v:0','-vf','showinfo,scale=480:270','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=log)
    size=480*270*3
    while True:
        buf=p.stdout.read(size)
        if not buf:break
        if len(buf)!=size:raise RuntimeError('partial decoded frame')
        ar=np.frombuffer(buf,dtype=np.uint8).reshape(270,480,3)
        luminance.append(float(ar.mean()))
        if count in selected:
            im=Image.fromarray(ar);im.save(Q/'decoded'/f'f{count:04d}.jpg',quality=95)
            kept.append(count)
        count+=1
    rc=p.wait()
logtext=(Q/'full-decode.log').read_text()
pts=[float(x) for x in re.findall(r' n:\s*\d+ pts:.*?pts_time:([\d.]+)',logtext)]
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Courier New.ttf',17)
for page in range(math.ceil(len(kept)/16)):
    board=Image.new('RGB',(1920,1176),(14,20,20)); d=ImageDraw.Draw(board)
    for j,n in enumerate(kept[page*16:page*16+16]):
        x=j%4*480;y=j//4*294
        board.paste(Image.open(Q/'decoded'/f'f{n:04d}.jpg'),(x,y))
        d.text((x+8,y+272),f'{n:03d}  |  {n/30:.3f} sec',font=font,fill=(225,219,194))
    board.save(Q/f'export-review-{page+1:02d}.jpg',quality=96)
filter_expr='+'.join(f'eq(n,{n})' for n in full)
extract=subprocess.run([F,'-hide_banner','-y','-loglevel','error','-i',str(V),'-vf',f"select='{filter_expr}'",'-fps_mode','passthrough','-q:v','2',str(Q/'decoded'/'full-%02d.jpg')],capture_output=True,text=True)
if extract.returncode:raise RuntimeError(extract.stderr)
audio=subprocess.run([F,'-hide_banner','-i',str(V),'-map','0:a:0','-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True)
(Q/'audio-export.log').write_text(audio.stderr)
audio_metrics=json.loads(audio.stderr[audio.stderr.rfind('{'):audio.stderr.rfind('}')+1])
result={
    'mp4':str(V),'sha256':hashlib.sha256(V.read_bytes()).hexdigest(),'bytes':V.stat().st_size,
    'video':'H.264 / yuv420p / 1920x1080 / 30 fps','audio':'AAC / 48kHz / stereo',
    'full_video_decode_exit_code':rc,'audio_decode_exit_code':audio.returncode,'decoded_frames':count,
    'pts_count':len(pts),'first_pts':pts[0] if pts else None,'last_pts':pts[-1] if pts else None,
    'pts_monotonic':all(a<b for a,b in zip(pts,pts[1:])),
    'max_pts_step_deviation_seconds':max(abs((b-a)-1/30) for a,b in zip(pts,pts[1:])) if len(pts)>1 else None,
    'frame_mean_range':[min(luminance),max(luminance)],
    'sampled_frame_count':len(kept),'sampled_frames':kept,'full_resolution_frames':full,
    'review_board_count':math.ceil(len(kept)/16),
    'export_audio_input_measurement':audio_metrics,
    'visual_review':'PENDING','continuous_av_watch_and_listening':'NOT_PERFORMED',
    'source':'All QA frames decoded from the exported MP4; authored previews are separate.'
}
(Q/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ['sampled_frames']},ensure_ascii=False,indent=2))
