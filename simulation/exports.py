"""Bundle the built replay, recording, CSS and inline artwork for file:// playback."""
import json
import re
from pathlib import Path


def export_replay(recording, path):
    dist = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
    if not (dist / 'index.html').exists():
        print('Replay frontend has not been built; exporting the legacy self-contained animation.')
        return False
    html = (dist / 'index.html').read_text(encoding='utf-8')
    html = '\n'.join(line.rstrip() for line in html.splitlines()) + '\n'
    scripts = []
    def script(match):
        source = (dist / match.group(1)).read_text(encoding='utf-8')
        source = source.replace('</script', '<\\/script')
        # Built bundle has no imports; a classic inline script also works on file://.
        scripts.append('<script>' + source + '</script>')
        return ''
    def style(match):
        return '<style>' + (dist / match.group(1)).read_text(encoding='utf-8') + '</style>'
    html = re.sub(r'<script[^>]*src="\./([^\"]+)"[^>]*></script>', script, html)
    html = re.sub(r'<link[^>]*href="\./([^\"]+\.css)"[^>]*>', style, html)
    html = '\n'.join(line.rstrip() for line in html.splitlines()) + '\n'
    data = json.dumps(recording,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    html = html.replace('<head>', '<head><script>window.__TINY_TOWN_RECORDING__=' + data + ';</script>',1)
    html = html.replace('</body>', ''.join(scripts) + '</body>')
    temporary = path.with_suffix('.html.tmp')
    temporary.write_text(html,encoding='utf-8')
    temporary.replace(path)
    print(f'Saved {path} - self-contained replay; open directly in a browser')
    return True
