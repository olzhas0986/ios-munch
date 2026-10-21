// Export APFS file contents and ownership metadata without FUSE or privileged mounts.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
#include <sys/stat.h>
#include <ApfsLib/ApfsContainer.h>
#include <ApfsLib/ApfsVolume.h>
#include <ApfsLib/ApfsDir.h>
#include <ApfsLib/Device.h>
#include <ApfsLib/GptPartitionMap.h>
#include <ApfsLib/Decmpfs.h>

static void require(bool ok, const std::string &what) {
    if (!ok) { std::fprintf(stderr, "APFS export failed: %s\n", what.c_str()); std::exit(1); }
}
static std::string json(const std::string &s) {
    std::string out="\"";
    for (unsigned char c : s) {
        if (c=='"' || c=='\\') { out+='\\'; out+=c; }
        else if (c<32) { char hex[7]; std::snprintf(hex,sizeof(hex),"\\u%04x",c); out+=hex; }
        else out+=c;
    }
    return out+'"';
}
static std::string destination;
static std::ofstream manifest;
static std::unordered_map<uint64_t,std::string> hardlinks;
static uint64_t files=0;

static void export_inode(ApfsDir &dir, uint64_t ino, const std::string &path, unsigned depth) {
    require(depth<128,"directory depth");
    ApfsDir::Inode info; require(dir.GetInode(info,ino),"inode "+path);
    const auto type=info.mode&S_IFMT;
    const std::string target=destination+path;
    std::string link;
    uint64_t size=info.ds_size;
    if (type==S_IFDIR) {
        require(::mkdir(target.c_str(),0700)==0,"mkdir "+target);
    } else if (type==S_IFLNK) {
        std::vector<uint8_t> attr;
        require(dir.GetAttribute(attr,ino,"com.apple.fs.symlink"),"symlink "+path);
        while (!attr.empty() && attr.back()==0) attr.pop_back();
        link.assign(attr.begin(),attr.end());
        // Record the link instead of creating it: host traversal must never escape the export.
        size=0;
    } else if (type==S_IFREG) {
        auto previous=hardlinks.find(ino);
        if (previous!=hardlinks.end()) {
            link=previous->second; size=0;
        } else {
            hardlinks[ino]=path;
            std::ofstream out(target,std::ios::binary|std::ios::out);
            require(bool(out),"create "+path);
            std::vector<uint8_t> attr,data;
            if (dir.GetAttribute(attr,ino,"com.apple.decmpfs")) {
                require(DecompressFile(dir,ino,data,attr),"decompress "+path);
                size=data.size();
                out.write(reinterpret_cast<const char*>(data.data()),data.size());
            } else {
                std::vector<uint8_t> buffer(1024*1024);
                for (uint64_t off=0;off<size;) {
                    size_t n=static_cast<size_t>(size-off>buffer.size()?buffer.size():size-off);
                    require(dir.ReadFile(buffer.data(),info.private_id,off,n),"read "+path);
                    out.write(reinterpret_cast<const char*>(buffer.data()),n); off+=n;
                }
            }
            out.close(); require(bool(out),"write "+path);
        }
    } else {
        // Preserve special-node metadata for a later filesystem importer.
        size=0;
    }
    manifest<<"{\"path\":"<<json(path)<<",\"inode\":"<<ino<<",\"mode\":"<<info.mode
            <<",\"uid\":"<<info.owner<<",\"gid\":"<<info.group<<",\"size\":"<<size
            <<",\"link\":"<<json(link)<<",\"flags\":"<<info.bsd_flags
            <<",\"rdev\":"<<info.rdev<<"}\n";
    require(bool(manifest),"manifest");
    files++;
    if (files%1000==0) std::fprintf(stderr,"Exported %llu entries\n",(unsigned long long)files);
    if (type==S_IFDIR) {
        std::vector<ApfsDir::DirRec> entries;
        require(dir.ListDirectory(entries,ino),"list "+path);
        for (auto &e:entries) {
            require(!e.name.empty() && e.name!="." && e.name!=".." && e.name.find('/')==std::string::npos,"unsafe name");
            export_inode(dir,e.file_id,path+"/"+e.name,depth+1);
        }
    }
}
int main(int argc,char **argv) {
    require(argc==4,"usage: munch-apfs-export IMAGE NEW_DIRECTORY MANIFEST.jsonl");
    g_debug=0;
    std::unique_ptr<Device> dev(Device::OpenDevice(argv[1])); require(bool(dev),"open device");
    uint64_t offset=0,size=dev->GetSize();
    GptPartitionMap gpt;
    if (gpt.LoadAndVerify(*dev)) {
        int index=gpt.FindFirstAPFSPartition();require(index>=0,"APFS partition");
        require(gpt.GetPartitionOffsetAndSize(index,offset,size),"APFS partition bounds");
    }
    ApfsContainer container(dev.get(),offset,size);require(container.Init(),"container");
    std::unique_ptr<ApfsVolume> volume(container.GetVolume(0));require(bool(volume),"volume");
    ApfsDir dir(*volume);
    destination=argv[2]; struct stat st;
    require(lstat(destination.c_str(),&st)!=0,"destination already exists");
    require(lstat(argv[3],&st)!=0,"manifest already exists");
    manifest.open(argv[3]);require(bool(manifest),"open manifest");
    export_inode(dir,2,"",0);
    manifest.close();require(bool(manifest),"close manifest");
    std::fprintf(stderr,"Export complete: %llu entries; links/owners/modes in manifest\n",(unsigned long long)files);
}
