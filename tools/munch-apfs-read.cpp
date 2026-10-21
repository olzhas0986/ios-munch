#include <cstdint>
#include <cstdio>
#include <cassert>
#include <fstream>
#include <sstream>
#include <memory>
#include <sys/stat.h>
#include <ApfsLib/ApfsContainer.h>
#include <ApfsLib/ApfsVolume.h>
#include <ApfsLib/ApfsDir.h>
#include <ApfsLib/Device.h>
#include <ApfsLib/Decmpfs.h>
int main(int argc,char**argv) {
 assert(argc==3||argc==4);g_debug=0;
 std::unique_ptr<Device> dev(Device::OpenDevice(argv[1]));assert(dev);
 ApfsContainer con(dev.get(),0,dev->GetSize());assert(con.Init());
 std::unique_ptr<ApfsVolume> vol(con.GetVolume(0));assert(vol);ApfsDir dir(*vol);
 uint64_t ino=2;std::istringstream path(argv[2]);std::string item;
 while(std::getline(path,item,'/')) {if(item.empty())continue;ApfsDir::DirRec rec;assert(dir.LookupName(rec,ino,item.c_str()));ino=rec.file_id;}
 ApfsDir::Inode info;assert(dir.GetInode(info,ino));
 if((info.mode&S_IFMT)==S_IFDIR) {std::vector<ApfsDir::DirRec> entries;assert(dir.ListDirectory(entries,ino));for(auto &r:entries){ApfsDir::Inode i;assert(dir.GetInode(i,r.file_id));printf("%06o %12llu %s\n",i.mode,(unsigned long long)i.ds_size,r.name.c_str());}return 0;}
 assert(argc==4);std::vector<uint8_t> data,attr;
 if(dir.GetAttribute(attr,ino,"com.apple.decmpfs")) {assert(DecompressFile(dir,ino,data,attr));}
 else {data.resize(info.ds_size);assert(dir.ReadFile(data.data(),info.private_id,0,data.size()));}
 std::ofstream out(argv[3],std::ios::binary);assert(out);out.write((const char*)data.data(),data.size());assert(out);printf("%s: %zu bytes\n",argv[2],data.size());
}
