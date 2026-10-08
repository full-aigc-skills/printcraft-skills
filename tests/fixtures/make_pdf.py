"""原创 CC0 PDF 夹具；无外部字体和模型，页面标记用于验证来源顺序。"""
from pathlib import Path

def make_pdf(path,labels=('PAGE-ALPHA','PAGE-BETA','PAGE-GAMMA')):
    objects=['<< /Type /Catalog /Pages 2 0 R >>',None,'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    kids=[]
    for label in labels:
        page=len(objects)+1;content=page+1;kids.append(f'{page} 0 R')
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content} 0 R >>')
        stream=f'BT /F1 24 Tf 72 700 Td ({label}) Tj ET\n'
        objects.append(f'<< /Length {len(stream)} >>\nstream\n{stream}endstream')
    objects[1]=f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(kids)} >>'
    data=b'%PDF-1.4\n';offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(data));data+=f'{i} 0 obj\n{obj}\nendobj\n'.encode('ascii')
    start=len(data);data+=f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode()
    for offset in offsets[1:]:data+=f'{offset:010d} 00000 n \n'.encode()
    data+=f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode();Path(path).write_bytes(data)
if __name__=='__main__':
    import sys
    make_pdf(sys.argv[1])
