#!/usr/bin/env python3
"""Read-only audit of embedded ABP2 asset metadata in an AB standalone HTML.

Does not decode meshopt buffers, export model assets, or modify the source.
Usage: python ar/tools/inspect_abp2.py AB-AR-Source-Baseline.html --output audit.json
"""
import argparse, base64, collections, gzip, json, re, hashlib
from pathlib import Path

PACK_RE = re.compile(r"ABAssetPack\.load\('data:application/octet-stream;base64,([A-Za-z0-9+/=]+)'\)")

def inspect(file: Path):
    text = file.read_text(encoding='utf-8')
    m = PACK_RE.search(text)
    if not m: raise ValueError('No embedded ABAssetPack.load data URL found')
    packed = base64.b64decode(m.group(1), validate=True)
    uncompressed = gzip.decompress(packed)
    if uncompressed[:4] != b'ABP2': raise ValueError('Not ABP2')
    n = int.from_bytes(uncompressed[4:8], 'little')
    meta = json.loads(uncompressed[8:8+n])
    if meta.get('schema') != 'AB.offline-assets.2': raise ValueError('Unexpected schema')
    buffers = meta.get('buffers', [])
    models = meta.get('assets', {}).get('AB_MOVING_ANATOMY_B64', {})
    return {
       'status': 'metadata-inspected; geometry not yet exported',
       'sourceFile': file.name,
       'sourceSha256': hashlib.sha256(file.read_bytes()).hexdigest(),
       'packGzipBytes': len(packed),
       'packRawBytes': len(uncompressed),
       'assetSchema': meta['schema'],
       'assetCount': len(meta['assets']),
       'bufferCount': len(buffers),
       'bufferFormatCounts': dict(collections.Counter(b.get('f') for b in buffers)),
       'reconstructedBufferBytes': sum(b.get('n', 0) for b in buffers),
       'movingAnatomyMeshRecords': len(models.get('meshes', [])),
       'movingAnatomyPaletteNames': len(models.get('palette', [])),
       'movingAnatomyTargetCharacters': list(models.get('targets', {})),
       'reliability': 'Index from embedded source bytes; GLB/USDZ export and iPhone AR not verified'
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=None)
    args=parser.parse_args()
    result=inspect(args.source)
    data=json.dumps(result, indent=2)+'\n'
    if args.output:
        args.output.write_text(data, encoding='utf-8')
    print(data)
if __name__=='__main__': main()
