#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#define N 131072
static uint8_t im[3][N]; static uint16_t tg[3];
static const char*fn[3]={"storico/produttore/MTLH-NB06-ec-250322/MTLH-NB06_E03-250322.BIN","dumps/EC0416.BIN","dumps/EC-V0.4.0-20250723-lettura1.bin"};
typedef struct{int s,e;int skA,skB;int fill;const char*n;}R;
static R rr[]={{0,N,0x4A,0x4C,-1,"all,skip4A"},{0,N,-1,-1,0,"all,4A=0"},{0,N,-1,-1,0xFF,"all,4A=FF"},{0,N,-1,-1,0x5A,"all,4A=5A"},{0,N,0x40,0x50,-1,"all,skipsig"},{0x50,N,-1,-1,-2,"50..end"},{0x100,N,-1,-1,-2,"100..end"},{0,0x10000,0x4A,0x4C,-1,"64k,skip4A"},{0,0x7F80,0x4A,0x4C,-1,"0-7F80,skip4A"},{0,0x8000,0x4A,0x4C,-1,"32k,skip4A"},{0x400,N,-1,-1,-2,"400..end"},{0,0x1000,0x4A,0x4C,-1,"4k,skip4A"}};
int main(){int nr=sizeof(rr)/sizeof(rr[0]);
 for(int i=0;i<3;i++){FILE*f=fopen(fn[i],"rb");if(!f||fread(im[i],1,N,f)!=N)return 1;fclose(f);tg[i]=(im[i][0x4A]<<8)|im[i][0x4B];printf("t%d %04x\n",i,tg[i]);}
 long hits=0;
 #pragma omp parallel for schedule(dynamic) reduction(+:hits)
 for(int p=0;p<65536;p++){
  uint16_t T[2][256];
  for(int b=0;b<256;b++){uint16_t c=b<<8;for(int k=0;k<8;k++)c=(c&0x8000)?(c<<1)^p:c<<1;T[0][b]=c;
   uint16_t q=0;for(int k=0;k<16;k++)if(p>>k&1)q|=1<<(15-k);c=b;for(int k=0;k<8;k++)c=(c&1)?(c>>1)^q:c>>1;T[1][b]=c;}
  for(int r=0;r<nr;r++){R*x=&rr[r];
   for(int m=0;m<2;m++){uint16_t cr[3];
    for(int i=0;i<3;i++){uint16_t c=0;for(int a=x->s;a<x->e;a++){if(a>=x->skA&&a<x->skB&&x->fill==-1)continue;uint8_t v=im[i][a];if((a==0x4A||a==0x4B)&&x->fill>=0)v=x->fill;
      if(m==0)c=(c<<8)^T[0][((c>>8)^v)&255];else c=(c>>8)^T[1][(c^v)&255];}
     cr[i]=c;
     if(i==1){int ok=0;for(int sw=0;sw<2;sw++){uint16_t a0=sw?(tg[0]>>8|tg[0]<<8):tg[0],a1=sw?(tg[1]>>8|tg[1]<<8):tg[1];if((cr[0]^a0)==(cr[1]^a1))ok=1;}if(!ok)break;}
     if(i==2){for(int sw=0;sw<2;sw++){uint16_t t[3];for(int j=0;j<3;j++)t[j]=sw?(tg[j]>>8|tg[j]<<8):tg[j];
       if((cr[0]^t[0])==(cr[1]^t[1])&&(cr[1]^t[1])==(cr[2]^t[2])){hits++;printf("HIT poly=%04x refl=%d range=%s swap=%d const=%04x\n",p,m,x->n,sw,cr[0]^t[0]);fflush(stdout);}}}
    }}}}
 printf("crc hits %ld\n",hits);
 // additive: sum8/16, word sums, xor, with both signs and byte order
 for(int r=0;r<nr;r++){R*x=&rr[r];for(int mode=0;mode<6;mode++){uint32_t v[3];
  for(int i=0;i<3;i++){uint32_t s=0;for(int a=x->s;a<x->e;a++){if(a>=x->skA&&a<x->skB&&x->fill==-1)continue;uint8_t b=im[i][a];if((a==0x4A||a==0x4B)&&x->fill>=0)b=x->fill;
    switch(mode){case 0:s+=b;break;case 1:s^=b;break;case 2:s+=(a&1)?b:(b<<8);break;case 3:s+=(a&1)?(b<<8):b;break;case 4:s^=(a&1)?b:(b<<8);break;case 5:s^=(a&1)?(b<<8):b;break;}}
   v[i]=s&0xffff;}
  for(int sw=0;sw<2;sw++)for(int sg=0;sg<2;sg++){uint16_t d[3];for(int j=0;j<3;j++){uint16_t t=sw?(tg[j]>>8|tg[j]<<8):tg[j];d[j]=sg?(uint16_t)(t+v[j]):(uint16_t)(t-v[j]);}
    if(d[0]==d[1]&&d[1]==d[2])printf("SUMHIT range=%s mode=%d sw=%d sg=%d c=%04x\n",x->n,mode,sw,sg,d[0]);}
 }}
 puts("done");return 0;}
