from pathlib import Path

src = Path('blogger-embed.html').read_text(encoding='utf-8')
if src.startswith('[full_width]'):
    src = src[len('[full_width]'):].lstrip('\r\n')

resize = r'''
<script>
(function(){
  function sendHeight(){
    var h=Math.max(document.documentElement.scrollHeight,document.body?document.body.scrollHeight:0);
    parent.postMessage({type:'fmbtc-height',height:h},'*');
  }
  window.addEventListener('load',sendHeight);
  window.addEventListener('resize',sendHeight);
  if(window.ResizeObserver){
    new ResizeObserver(sendHeight).observe(document.documentElement);
  }
  new MutationObserver(function(){requestAnimationFrame(sendHeight)}).observe(document.documentElement,{subtree:true,childList:true,attributes:true});
  setTimeout(sendHeight,250);
  setTimeout(sendHeight,1000);
  setTimeout(sendHeight,2500);
})();
</script>
'''

html = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>FM Blog Transfer Centre</title>
<style>html,body{margin:0!important;padding:0!important;width:100%!important;min-height:100%!important;background:#080a0f!important;overflow-x:hidden!important}body{font-family:Arial,sans-serif}</style>
</head>
<body>
''' + src + resize + '\n</body>\n</html>\n'

Path('transfer-centre-app-v4.html').write_text(html,encoding='utf-8')
print('Built transfer-centre-app-v4.html', len(html), 'bytes')
