"""
Generate photorealistic talking avatar videos using real portrait photo.
Uses Playwright + Canvas + MediaRecorder.
"""
from playwright.sync_api import sync_playwright
import os, base64, json

VIDEO_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'avatar-videos')
PORTRAIT_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'portrait.jpg')
os.makedirs(VIDEO_DIR, exist_ok=True)

# Read and encode portrait as base64 data URL
portrait_b64 = ''
if os.path.exists(PORTRAIT_PATH):
    with open(PORTRAIT_PATH, 'rb') as f:
        portrait_b64 = 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode()

SCRIPTS = {
    'greeting.webm': ['您好，欢迎使用', 'AI视频客服系统', '我是智能客服', '请问有什么可以帮您？'],
    'claim-guide.webm': ['理赔流程', '1.拨打95511报案', '2.准备身份证保单医疗记录', '3.提交审核3-5工作日', '4.赔付到账'],
    'insurance-intro.webm': ['我们提供丰富产品', '寿险·健康险', '意外险·车险', '24小时在线投保'],
    'refund-info.webm': ['退保规则', '犹豫期10天内全额退款', '之后按现金价值返还', '需保单+身份证+银行卡'],
    'renewal-info.webm': ['续保政策', '到期前30天可办理', '续保无需重新核保', '按原费率或调整后计算'],
}

def generate(lines, outpath):
    lines_json = json.dumps(lines, ensure_ascii=False)
    portrait_data = portrait_b64

    html = f'''<!DOCTYPE html><html>
<head><style>*{{margin:0;padding:0}}body{{overflow:hidden;background:#0a0a1a}}</style></head>
<body>
<canvas id="c" width="640" height="480"></canvas>
<script>
var L={lines_json};
var IMG="{portrait_data}";
var c=document.getElementById("c"),x=c.getContext("2d");
var frame=0,chunks=[],img=new Image();
var s=c.captureStream(25);
var r=new MediaRecorder(s,{{mimeType:"video/webm;codecs=vp8",videoBitsPerSecond:800000}});
r.ondataavailable=function(e){{chunks.push(e.data)}};
r.onstop=function(){{var b=new Blob(chunks,{{type:"video/webm"}});var fr=new FileReader();fr.onload=function(){{window._vd=fr.result}};fr.readAsDataURL(b)}};

img.onload=function(){{
  r.start();
  // Speak each line with pauses
  var lines=L, li=0, fps=25, totalFrames=lines.length*50+20;
  
  function animate(){{
    var w=640,h=480,t=frame/fps;
    x.clearRect(0,0,w,h);
    
    // Background
    x.fillStyle="#0a0a1a";x.fillRect(0,0,w,h);
    
    // Ken Burns effect on photo
    var zoom=1+Math.sin(t*0.4)*0.02+0.02;
    var px=Math.sin(t*0.3)*4;
    var py=Math.sin(t*0.5+1)*3;
    x.save();
    x.translate(w/2+px,h/2+py);
    x.scale(zoom,zoom);
    x.translate(-w/2,-h/2);
    x.drawImage(img,(w-640)/2,(h-640)/2,640,640);
    x.restore();
    
    // Vignette
    var vg=x.createRadialGradient(w/2,h/2,w*0.35,w/2,h/2,w*0.75);
    vg.addColorStop(0,"rgba(0,0,0,0)");vg.addColorStop(1,"rgba(0,0,0,0.15)");
    x.fillStyle=vg;x.fillRect(0,0,w,h);
    
    // Determine which line to show
    var li=Math.floor(frame/40);
    if(li>=lines.length)li=lines.length-1;
    var word=lines[li];
    var lineProgress=(frame%40)/40;
    
    // Mouth animation
    var mouthX=w*0.5,mouthY=h*0.70;
    var mouthOpen=0;
    if(lineProgress>0.1&&lineProgress<0.9){{
      // Simulate speaking: open/close at speech rate
      var speakT=frame*0.15;
      mouthOpen=0.3+Math.abs(Math.sin(speakT*2))*0.5+Math.sin(speakT*5)*0.1;
    }}
    
    if(mouthOpen>0.03){{
      // Inner mouth dark
      x.beginPath();
      x.ellipse(mouthX,mouthY,mouthOpen*45,mouthOpen*30,0,0,Math.PI*2);
      x.fillStyle="#150404";x.fill();
      
      // Lips
      x.beginPath();
      x.moveTo(mouthX-30,mouthY-5);
      x.quadraticCurveTo(mouthX,mouthY-mouthOpen*12,mouthX+30,mouthY-5);
      x.strokeStyle="#c06050";x.lineWidth=3;x.stroke();
      
      x.beginPath();
      x.moveTo(mouthX-30,mouthY-5);
      x.quadraticCurveTo(mouthX,mouthY+mouthOpen*8,mouthX+30,mouthY-5);
      x.strokeStyle="#b85845";x.lineWidth=2.5;x.fillStyle="rgba(200,120,100,0.4)";
      x.fill();x.stroke();
    }}
    
    // Speech bubble with text
    x.fillStyle="rgba(0,0,0,0.6)";
    x.beginPath();x.roundRect(w*0.1,h-75,w*0.8,55,12);x.fill();
    x.fillStyle="#fff";x.font="bold 18px sans-serif";
    x.textAlign="center";x.fillText(word,w/2,h-38);
    
    frame++;
    if(frame<totalFrames)requestAnimationFrame(animate);
    else r.stop();
  }}
  animate();
}};
img.src=IMG;
</script></body></html>'''

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 640, 'height': 480})
        page.set_content(html)
        
        # Wait for video to finish recording
        result = page.evaluate("""
            () => new Promise(resolve => {
                const check = setInterval(() => {
                    if (window._vd) { clearInterval(check); resolve(window._vd); }
                }, 200);
            })
        """)
        
        # Save as webm
        if result and ',' in result:
            data = base64.b64decode(result.split(',')[1])
            with open(os.path.join(VIDEO_DIR, outpath), 'wb') as f:
                f.write(data)
            print(f'  {outpath}: {len(data)//1024}KB')
        
        browser.close()

if __name__ == '__main__':
    print('Generating photorealistic avatar videos...')
    for name, lines in SCRIPTS.items():
        print(f'  {name}...')
        generate(lines, name)
    print('Done!')
