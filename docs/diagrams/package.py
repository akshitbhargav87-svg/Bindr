"""Package the editable scenes, self-contained generators and rendered exports."""
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parent
parent=root.parent
# Keep repository copies as documentation; standalone source produces the ZIPs.
if root.name=='diagrams':
    print('Repository diagram sources are ready; use the standalone pack for distribution ZIPs.')
else:
    files=[p for p in root.iterdir() if p.is_file() and p.suffix in {'.py','.md','.svg','.excalidraw','.png','.pdf','.html'}]
    files+=list((root/'assets').glob('*'))
    for name in ('bindr-flowcharts.zip','bindr-flowcharts-16x9.zip'):
        with zipfile.ZipFile(parent/name,'w',zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(files):
                if path.is_file():bundle.write(path,Path('bindr-flowcharts')/path.relative_to(root))
        print(parent/name)
