// Generate code-native vector/raster assets and a stable PUBLIC development key.
import { createHash, generateKeyPairSync } from 'node:crypto';
import { mkdirSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { deflateSync } from 'node:zlib';
mkdirSync('public/icon', { recursive: true });
const circles = [[64,32,23],[94,54,23],[83,90,23],[45,90,23],[34,54,23],[64,64,16]];
writeFileSync('public/icon/flower.svg', `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">${circles.map(([cx,cy,r],i)=>`<circle cx="${cx}" cy="${cy}" r="${r}" fill="${i===5?'#fbbf24':'#8b5cf6'}"/>`).join('')}</svg>\n`);
const crc = data => { let c=0xffffffff; for(const v of data){ c^=v; for(let j=0;j<8;j++)c=(c>>>1)^((c&1)?0xedb88320:0); } return (c^0xffffffff)>>>0; };
const chunk = (type,data) => { const t=Buffer.from(type), b=Buffer.alloc(12+data.length); b.writeUInt32BE(data.length); t.copy(b,4); data.copy(b,8); b.writeUInt32BE(crc(Buffer.concat([t,data])),8+data.length); return b; };
for(const size of [16,32,48,128,256]) {
    const raw=Buffer.alloc(size*(1+size*4));
    for(let y=0;y<size;y++)for(let x=0;x<size;x++) {
        const sums=[0,0,0,0];
        for(let sy=0;sy<4;sy++)for(let sx=0;sx<4;sx++) {
            const px=(x+(sx+.5)/4)*128/size,py=(y+(sy+.5)/4)*128/size; let color;
            circles.forEach(([cx,cy,r],i)=>{ if((px-cx)**2+(py-cy)**2<=r*r)color=i===5?[251,191,36]:[139,92,246]; });
            if(color){ color.forEach((v,i)=>sums[i]+=v); sums[3]++; }
        }
        const off=y*(1+size*4)+1+x*4;
        for(let i=0;i<3;i++)raw[off+i]=sums[3]?Math.round(sums[i]/sums[3]):0; raw[off+3]=Math.round(sums[3]*255/16);
    }
    const header=Buffer.alloc(13); header.writeUInt32BE(size); header.writeUInt32BE(size,4); header[8]=8; header[9]=6;
    const png=Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',deflateSync(raw)),chunk('IEND',Buffer.alloc(0))]);
    writeFileSync(`public/icon/${size}.png`,png);
    if(size===256){ const ico=Buffer.alloc(22); ico.writeUInt16LE(1,2); ico.writeUInt16LE(1,4); ico.writeUInt16LE(1,10); ico.writeUInt16LE(32,12); ico.writeUInt32LE(png.length,14); ico.writeUInt32LE(22,18); writeFileSync('public/icon/flower.ico',Buffer.concat([ico,png])); }
}
if(!existsSync('preview-identity.json')) {
    const {publicKey}=generateKeyPairSync('rsa',{modulusLength:2048}); // Private key is never retained.
    const der=publicKey.export({type:'spki',format:'der'});
    const id=createHash('sha256').update(der).digest('hex').slice(0,32).split('').map(v=>String.fromCharCode(97+parseInt(v,16))).join('');
    writeFileSync('preview-identity.json',JSON.stringify({developmentOnly:true,publicKey:der.toString('base64'),chromeId:id},null,2)+'\n');
}
console.log('Flower assets generated; development identity:', JSON.parse(readFileSync('preview-identity.json','utf8')).chromeId);
