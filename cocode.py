import pathlib
import clang.cindex
import re
import argparse


def getfiles_fromdir(dirname, extensions={'.cpp', '.hpp', '.cc', '.h', 'cxx', 'c'}):
    '''Get cpp source files from directory
    Returns: list[Pathobj]
    '''
    p = pathlib.Path(dirname)
    filelist = []
    for path in p.glob(r'**/*'):
        if path.suffix in extensions:
            filelist.append(path)
    
    return filelist

def remove_comments(filehandle, location):
    '''Remove the comment according to the location of the file.
    param filehandle: Python's file object
    param location: Sourcelocation, provided by libclang
    '''
    file_content = filehandle.read()
    comment_pattern = re.compile(r'\/{2,}.*|\/\*[\s\S]+?\*\/')  # Single match
    
    offset = location.offset
    filehandle.seek(offset)
    new_content = filehandle.read()
    
    match = re.search(comment_pattern, new_content)
    if match:
        pass
        # TODO: replace the pattern content accrocding to regex expression.
        

def cppparser(filepath):
    f = open(filepath, 'r+')
    idx = clang.cindex.Index.create()
    raw_tu = idx.parse(filepath, args=['-std=c++11'])
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
            new_file = filepath.parent / pathlib.Path('new_'+filepath.name)
            comment_location = r_t.location
            with open(new_file, "w") as new_f:
                remove_comments(new_f, comment_location)
        
    
    f.close()
    
def run(dirname=None, filename=None):
    clang.cindex.Config.set_library_file("D:\Project\cocodeRemover\libclang.dll")
    if dirname:
        sourcefileList = getfiles_fromdir(dirname)
        for sourcefile in sourcefileList:
            cppparser(sourcefile)
    if filename:
        cppparser(filename)
    

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
    
    args = argparser.parse_args()
    if args.dir:
        run(dirname=args.dir)
        
    elif args.file:
        run(filename=args.file)