/* Guarded raw HFS image installer for Munch recovery. No partition-table writes. */
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <linux/fs.h>

#define ROOT_BYTES (UINT64_C(16)*1024*1024*1024)
#define ROOT_FIRST UINT64_C(26455808)
#define DISK_BLOCKS UINT64_C(30650368)
#define CHUNK (1024*1024)
struct sha256 { uint32_t h[8]; uint64_t bytes; unsigned used; uint8_t block[64]; };
static uint32_t rotate(uint32_t x,unsigned n) { return (x>>n)|(x<<(32-n)); }
static uint32_t be32(const uint8_t *p) { return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3]; }
static uint32_t le32(const uint8_t *p) { return ((uint32_t)p[3]<<24)|((uint32_t)p[2]<<16)|((uint32_t)p[1]<<8)|p[0]; }
static uint64_t le64(const uint8_t *p) { return le32(p)|((uint64_t)le32(p+4)<<32); }
static void sha_init(struct sha256 *s) {
    static const uint32_t initial[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    memcpy(s->h,initial,sizeof(initial));s->bytes=0;s->used=0;
}
static void sha_block(struct sha256 *s,const uint8_t *p) {
    static const uint32_t k[64]={
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
    uint32_t w[64];for(unsigned i=0;i<16;i++)w[i]=be32(p+4*i);
    for(unsigned i=16;i<64;i++){uint32_t x=w[i-15],y=w[i-2];w[i]=(rotate(x,7)^rotate(x,18)^(x>>3))+w[i-16]+(rotate(y,17)^rotate(y,19)^(y>>10))+w[i-7];}
    uint32_t a=s->h[0],b=s->h[1],c=s->h[2],d=s->h[3],e=s->h[4],f=s->h[5],g=s->h[6],h=s->h[7];
    for(unsigned i=0;i<64;i++){uint32_t t1=h+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+k[i]+w[i];uint32_t t2=(rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;}
    s->h[0]+=a;s->h[1]+=b;s->h[2]+=c;s->h[3]+=d;s->h[4]+=e;s->h[5]+=f;s->h[6]+=g;s->h[7]+=h;
}
static void sha_update(struct sha256 *s,const void *data,size_t n) {
    const uint8_t *p=data;s->bytes+=n;
    while(n){size_t take=64-s->used;if(take>n)take=n;memcpy(s->block+s->used,p,take);s->used+=(unsigned)take;p+=take;n-=take;if(s->used==64){sha_block(s,s->block);s->used=0;}}
}
static void sha_final(struct sha256 *s,char out[65]) {
    uint64_t bits=s->bytes*8;uint8_t pad[128]={0x80};unsigned n=s->used<56?56-s->used:120-s->used;
    sha_update(s,pad,n);for(unsigned i=0;i<8;i++)pad[i]=(uint8_t)(bits>>(56-8*i));sha_update(s,pad,8);
    for(unsigned i=0;i<8;i++) { snprintf(out+8*i,9,"%08x",s->h[i]); }
    out[64]=0;
}
static void die(const char *message) { fprintf(stderr,"MUNCH INSTALL: %s (errno=%d)\n",message,errno);exit(1); }
static uint32_t crc32_gpt(const uint8_t *p,size_t n) {uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&(0u-(c&1)));}return ~c;}
static int gpt_valid(const uint8_t *h,const uint8_t *entries) {
    uint8_t copy[92];memcpy(copy,h,92);memset(copy+16,0,4);
    if(memcmp(h,"EFI PART",8)||le32(h+8)!=0x10000||le32(h+12)!=92||crc32_gpt(copy,92)!=le32(h+16))return 0;
    if(le64(h+24)!=1||le64(h+32)!=DISK_BLOCKS-1||le64(h+40)!=6||le64(h+48)!=DISK_BLOCKS-6||le64(h+72)!=2||le32(h+80)!=64||le32(h+84)!=128||crc32_gpt(entries,8192)!=le32(h+88))return 0;
    const uint8_t *root=entries+34*128,*data=entries+33*128;
    static const uint8_t label[16]={'i',0,'o',0,'s',0,'r',0,'o',0,'o',0,'t',0,0,0};
    static const uint8_t type[16]={0,0x53,0x46,0x48,0,0,0xaa,0x11,0xaa,0x11,0,0x30,0x65,0x43,0xec,0xac};
    return !memcmp(root,type,16)&&!memcmp(root+56,label,16)&&le64(root+32)==ROOT_FIRST&&le64(root+40)==ROOT_FIRST+ROOT_BYTES/4096-1&&le64(data+32)==2949120&&le64(data+40)==ROOT_FIRST-1;
}
static uint64_t number(const char *path) {FILE *f=fopen(path,"r");unsigned long long n;if(!f||fscanf(f,"%llu",&n)!=1)die("cannot read block geometry");fclose(f);return (uint64_t)n;}
static void read_exact(int fd,void *p,size_t n,off_t off) {size_t done=0;while(done<n){ssize_t r=pread(fd,(uint8_t*)p+done,n-done,off+(off_t)done);if(r<0&&errno==EINTR)continue;if(r<=0)die("short device read");done+=(size_t)r;}}
static void validate_disk(void) {
    if(number("/sys/class/block/sda/size")!=DISK_BLOCKS*8||number("/sys/class/block/sda/queue/logical_block_size")!=4096||number("/sys/class/block/sda35/start")!=ROOT_FIRST*8||number("/sys/class/block/sda35/size")!=ROOT_BYTES/512)die("unexpected Munch partition geometry");
    int fd=open("/dev/block/sda",O_RDONLY);if(fd<0)die("cannot open GPT read-only");
    uint8_t h[4096],e[8192];read_exact(fd,h,sizeof(h),4096);read_exact(fd,e,sizeof(e),8192);if(!gpt_valid(h,e))die("GPT or iosroot entry mismatch");
    uint8_t backup[4096],array[8192];read_exact(fd,backup,sizeof(backup),(DISK_BLOCKS-1)*4096);read_exact(fd,array,sizeof(array),(DISK_BLOCKS-5)*4096);
    uint8_t temp[92];memcpy(temp,backup,92);memset(temp+16,0,4);
    if(memcmp(backup,"EFI PART",8)||crc32_gpt(temp,92)!=le32(backup+16)||le64(backup+24)!=DISK_BLOCKS-1||le64(backup+32)!=1||le64(backup+72)!=DISK_BLOCKS-5||memcmp(h+56,backup+56,16)||memcmp(e,array,sizeof(e)))die("backup GPT mismatch");
    close(fd);
}
static int image_header(const uint8_t *p) {return p[1024]=='H'&&(p[1025]=='+'||p[1025]=='X')&&be32(p+1024+40)==4096&&be32(p+1024+44)==ROOT_BYTES/4096;}
int main(int argc,char **argv) {
    static uint8_t buffer[CHUNK];struct sha256 hash;char digest[65];
    if(argc==2&&!strcmp(argv[1],"--sha256")){sha_init(&hash);size_t n;while((n=fread(buffer,1,sizeof(buffer),stdin)))sha_update(&hash,buffer,n);if(ferror(stdin))die("input read failed");sha_final(&hash,digest);puts(digest);return 0;}
    if(argc==2&&!strcmp(argv[1],"--check")){if(getuid()!=0) { die("root recovery required"); }
    validate_disk();puts("MUNCH INSTALL: geometry and both GPT copies verified; no writes");return 0;}
    if(argc!=3||strcmp(argv[1],"--apply")||strlen(argv[2])!=64){fprintf(stderr,"Usage: munch-root-write --check | --sha256 | --apply EXPECTED_SHA256 < image\n");return 2;}
    for(unsigned i=0;i<64;i++)if(!((argv[2][i]>='0'&&argv[2][i]<='9')||(argv[2][i]>='a'&&argv[2][i]<='f')))die("invalid expected hash");
    if(getuid()!=0) { die("root recovery required"); }
    validate_disk();
    size_t first=fread(buffer,1,sizeof(buffer),stdin);if(first<1536||!image_header(buffer))die("invalid 16 GiB HFS image header");
    int fd=open("/dev/block/sda35",O_RDWR|O_EXCL);if(fd<0)die("cannot exclusively open iosroot; it may be mounted");
    struct stat st;uint64_t bytes=0;unsigned sector=0;if(fstat(fd,&st)||!S_ISBLK(st.st_mode)||ioctl(fd,BLKGETSIZE64,&bytes)||ioctl(fd,BLKSSZGET,&sector)||bytes!=ROOT_BYTES||sector!=4096)die("wrong target block device");
    sha_init(&hash);uint64_t written=0;size_t n=first;
    do {if(n>ROOT_BYTES-written)die("image exceeds iosroot");sha_update(&hash,buffer,n);size_t done=0;while(done<n){ssize_t w=pwrite(fd,buffer+done,n-done,(off_t)(written+done));if(w<0&&errno==EINTR)continue;if(w<=0)die("iosroot write failed");done+=(size_t)w;}written+=n;if(!(written%(256*1024*1024)))fprintf(stderr,"MUNCH INSTALL: %llu / 16384 MiB written\n",(unsigned long long)(written>>20));}while((n=fread(buffer,1,sizeof(buffer),stdin)));
    if(ferror(stdin)||written!=ROOT_BYTES) { die("incomplete image; iosroot is not ready"); }
    sha_final(&hash,digest);if(strcmp(digest,argv[2]))die("input SHA256 mismatch; iosroot is not ready");if(fsync(fd))die("device sync failed");
    fprintf(stderr,"MUNCH INSTALL: reading iosroot back for SHA256 verification\n");sha_init(&hash);for(uint64_t off=0;off<ROOT_BYTES;off+=sizeof(buffer)){read_exact(fd,buffer,sizeof(buffer),(off_t)off);sha_update(&hash,buffer,sizeof(buffer));if(!((off+sizeof(buffer))%(512*1024*1024)))fprintf(stderr,"MUNCH INSTALL: %llu / 16384 MiB verified\n",(unsigned long long)((off+sizeof(buffer))>>20));}sha_final(&hash,digest);if(strcmp(digest,argv[2]))die("readback SHA256 mismatch");if(close(fd))die("device close failed");puts("MUNCH INSTALL: rootfs installed and readback verified");return 0;
}
