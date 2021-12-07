import pathlib
import clang.cindex
import re
import argparse


def getfiles_fromdir(dirname, extensions={'.cpp', '.hpp', '.cc', '.h', 'cxx', 'c'}):
    p = pathlib.Path(dirname)
    filelist = []
    for path in p.glob(r'**/*'):
        if path.suffix in extensions:
            filelist.append(path)
    
    return filelist

def cppparser(filename, new_flag):
    f = open(filename, 'r+')
    idx = clang.cindex.Index.create()
    raw_tu = idx.parse(filename, args=['-std=c++11'])
    raw_tu_tokens = raw_tu.get_tokens(extent=raw_tu.cursor.extent)
    zh_cn_pattern = r"[\u4e00-\u9fa5]"
    
    for r_t in raw_tu_tokens:
        if r_t.kind.name != "COMMENT":
            continue
        
        print(f"t_kindname: {r_t.kind.name}, t_spelling: {r_t.spelling}")
        print("-------------------------------------------------\n")
        comment_content = r_t.spelling
        zhcn_match = re.search(zh_cn_pattern, comment_content)
        if zhcn_match:
            continue
        
        if comment_content.startswith('//') and ("copyright" not in comment_content.lower()):
            comment_content = comment_content.lstrip('//')
        
        if comment_content.startswith("/*") and ("copyright" not in comment_content.lower()):
            comment_content = comment_content.lstrip("/*")
            comment_content = comment_content.rstrip("*/")
            
        idx_comment = clang.cindex.Index.create()
        tu = idx_comment.parse('tmp.cpp',
                               args=['-std=c++11'], 
                               unsaved_files=[('tmp.cpp', comment_content)],
                               options=0
        )
        comment_location = r_t.location
        
        isEnglishComment = 0
        isidfr = lambda x: x == "IDENTIFIER"
        kindname_list = []
        tu_tokens = tu.get_tokens(extent=tu.cursor.extent)
        
        for t in tu_tokens:
            kindname_list.append(t.kind.name)
            print(f"t_kindname = {t.kind.name}, t_spelling = {t.spelling}")
            
        for i in range(len(kindname_list) - 3):
            # Model: If the identifier appears three times continuously, it can be considered as an English comment block.
            if isidfr(kindname_list[i]) and isidfr(kindname_list[i+1]) and isidfr(kindname_list[i+2]):
                isEnglishComment = 1
                break
                
        if isEnglishComment:
            continue
        
        else:
            if new_flag == 1:    
                new_file = "new_" + filename
                with open(new_file, "w") as new_f:
                    pass
            else:
                pass
        
    
    f.close()
    
def run(dirname=None, filename=None, new_flag=1):
    clang.cindex.Config.set_library_file("D:\Project\cocodeRemover\libclang.dll")
    if dirname:
        sourcefileList = getfiles_fromdir(dirname)
        for sourcefile in sourcefileList:
            cppparser(sourcefile, new_flag)
    if filename:
        cppparser(filename, new_flag)
    

if __name__ == "__main__":
    argparser = argparse.ArgumentParser("Remove the comment-out cpp code")
    argparser.add_argument('--dir',
                           default='tests',
                           nargs='?',
                           help="Name of directory for us to process"
    )
    
    argparser.add_argument('--file',
                           help="A single file for us to process"
    )
    
    argparser.add_argument('--newflag',
                            default=1,
                            nargs='?',
                            help="Whether to generate new file based on source code"
    )
    
    args = argparser.parse_args()
    if args.dir:
        run(dirname=args.dir, new_flag=args.newflag)
        
    elif args.file:
        run(filename=args.file, new_flag=args.new_flag)